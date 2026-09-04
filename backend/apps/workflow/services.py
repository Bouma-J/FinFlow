"""
Logique métier du moteur de workflow (démarrage, décisions, réserves).
"""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import (
    ApprovalCondition,
    ApprovalStep,
    ApprovalTask,
    WorkflowDefinition,
    WorkflowInstance,
)


class WorkflowError(Exception):
    """Erreur métier du moteur de workflow."""


def get_active_definition(tenant_id, target_type):
    return (
        WorkflowDefinition.all_tenants.filter(
            tenant_id=tenant_id, target_type=target_type, is_active=True
        )
        .order_by("-version")
        .first()
    )


def select_definition(tenant_id, target_type, amount, risk_level=None):
    """Choisit le circuit adapté au dossier parmi les circuits actifs.

    Plusieurs circuits peuvent être actifs simultanément (p. ex. une tranche de
    montant par circuit). On retient le premier circuit actif dont au moins une
    étape s'applique au couple (montant, niveau de risque). Les circuits les plus
    récents (version décroissante) sont prioritaires en cas de recouvrement.
    """
    definitions = WorkflowDefinition.all_tenants.filter(
        tenant_id=tenant_id, target_type=target_type, is_active=True
    ).order_by("-version")
    for definition in definitions:
        if _applicable_steps(definition, amount, risk_level):
            return definition
    return None


def definition_is_used(definition):
    """Indique si le circuit a déjà servi pour au moins un dossier."""
    return WorkflowInstance.objects.filter(definition=definition).exists()


def ensure_definition_editable(definition):
    """Bloque la modification structurelle d'un circuit déjà utilisé."""
    if definition_is_used(definition):
        raise WorkflowError(
            "Ce circuit a déjà été utilisé dans des dossiers. "
            "Créez une nouvelle version pour ajouter, modifier ou supprimer "
            "des étapes."
        )


def _applicable_steps(definition, amount, risk_level):
    steps = definition.steps.order_by("order")
    return [s for s in steps if s.applies_to(amount, risk_level)]


def _get_credit_application(instance):
    target = instance.target
    if target is None:
        return None
    from apps.credits.models import CreditApplication

    return target if isinstance(target, CreditApplication) else None


def _active_instance(application):
    """Dernière instance de circuit encore active pour ce dossier."""
    content_type = ContentType.objects.get_for_model(application.__class__)
    return (
        WorkflowInstance.all_tenants.filter(
            content_type=content_type,
            object_id=application.pk,
            status__in=[
                WorkflowInstance.Status.IN_PROGRESS,
                WorkflowInstance.Status.AWAITING_CONDITIONS,
            ],
        )
        .order_by("-created_at")
        .first()
    )


def _pending_conditions_exist(application):
    """Réserves non validées rattachées au cycle d'approbation actif.

    On ne considère que les réserves du cycle en cours : celles d'un cycle
    abandonné (dossier renvoyé puis re-soumis, soumission annulée) ne doivent
    pas bloquer le nouveau circuit.
    """
    qs = ApprovalCondition.objects.filter(application=application).exclude(
        status=ApprovalCondition.Status.VALIDATED
    )
    active = _active_instance(application)
    if active is not None:
        qs = qs.filter(task__instance=active)
    return qs.exists()


def _append_suspensive_conditions(application, lines):
    """Ajoute les réserves au champ conditions suspensives du dossier."""
    text = "\n".join(line.strip() for line in lines if line and line.strip())
    if not text:
        return
    if application.suspensive_conditions:
        application.suspensive_conditions = (
            f"{application.suspensive_conditions.rstrip()}\n{text}"
        )
    else:
        application.suspensive_conditions = text
    application.save(update_fields=["suspensive_conditions", "updated_at"])


def _create_conditions(task, application, user, reserves):
    now = timezone.now()
    for line in reserves:
        desc = line.strip()
        if not desc:
            continue
        ApprovalCondition.objects.create(
            tenant_id=application.tenant_id,
            application=application,
            task=task,
            description=desc,
            issued_by=user,
            issued_at=now,
        )
    _append_suspensive_conditions(application, reserves)


@transaction.atomic
def start_workflow(target, amount, risk_level=None, definition=None, target_type=None):
    """Démarre un circuit d'approbation pour l'objet cible."""
    tenant_id = target.tenant_id
    if target_type is None:
        if definition is not None:
            target_type = definition.target_type
        else:
            target_type = WorkflowDefinition.TargetType.CREDIT
    if definition is None:
        definition = select_definition(
            tenant_id,
            target_type,
            amount,
            risk_level,
        )
    if definition is None:
        # On distingue « aucun circuit actif » de « aucun circuit ne couvre le
        # montant » pour guider le paramétrage.
        has_active = WorkflowDefinition.all_tenants.filter(
            tenant_id=tenant_id,
            target_type=target_type,
            is_active=True,
        ).exists()
        label = dict(WorkflowDefinition.TargetType.choices).get(
            target_type, target_type
        )
        if not has_active:
            raise WorkflowError(
                f"Aucun circuit d'approbation actif ({label}) pour cette filiale."
            )
        raise WorkflowError(
            f"Aucun circuit d'approbation ({label}) ne couvre le montant. "
            "Vérifiez les tranches de montant des circuits configurés."
        )

    steps = _applicable_steps(definition, amount, risk_level)
    if not steps:
        raise WorkflowError("Aucune étape applicable pour ce dossier.")

    instance = WorkflowInstance.objects.create(
        definition=definition,
        content_type=ContentType.objects.get_for_model(target.__class__),
        object_id=target.pk,
        amount=amount,
        risk_level=risk_level,
        status=WorkflowInstance.Status.IN_PROGRESS,
        current_order=steps[0].order,
    )
    _open_tasks_for_order(instance, steps, steps[0].order)
    return instance


def _sync_target_status(instance):
    """Répercute l'état du circuit sur l'objet cible."""
    target = instance.target
    if target is None:
        return
    from apps.credits.models import CreditApplication
    from apps.guarantees.models import DationRequest, GuaranteeReleaseRequest
    from apps.guarantees.process_services import (
        complete_dation_request,
        complete_release_request,
    )

    if isinstance(target, CreditApplication):
        mapping = {
            WorkflowInstance.Status.APPROVED: CreditApplication.Status.APPROVED,
            WorkflowInstance.Status.REJECTED: CreditApplication.Status.REJECTED,
            WorkflowInstance.Status.RETURNED: CreditApplication.Status.RETURNED,
        }
        new_status = mapping.get(instance.status)
        if new_status:
            target.status = new_status
            if new_status == CreditApplication.Status.APPROVED:
                target.decision_date = timezone.now().date()
                if target.amount_approved is None:
                    target.amount_approved = (
                        target.amount_proposed or target.amount_requested
                    )
                if target.interest_rate is None:
                    target.interest_rate = target.product.interest_rate
            target.save()
        return

    if isinstance(target, GuaranteeReleaseRequest):
        mapping = {
            WorkflowInstance.Status.REJECTED: GuaranteeReleaseRequest.Status.REJECTED,
            WorkflowInstance.Status.RETURNED: GuaranteeReleaseRequest.Status.RETURNED,
        }
        if instance.status == WorkflowInstance.Status.APPROVED:
            target.status = GuaranteeReleaseRequest.Status.APPROVED
            target.save(update_fields=["status", "updated_at"])
            # Clôture uniquement si l'acte signé est déjà déposé (règle A).
            if target.has_signed_acte():
                from apps.guarantees.process_services import ProcessError

                try:
                    complete_release_request(target)
                except ProcessError:
                    pass
            return
        new_status = mapping.get(instance.status)
        if new_status:
            target.status = new_status
            target.save(update_fields=["status", "updated_at"])
        return

    if isinstance(target, DationRequest):
        mapping = {
            WorkflowInstance.Status.REJECTED: DationRequest.Status.REJECTED,
            WorkflowInstance.Status.RETURNED: DationRequest.Status.RETURNED,
        }
        if instance.status == WorkflowInstance.Status.APPROVED:
            target.status = DationRequest.Status.APPROVED
            target.save(update_fields=["status", "updated_at"])
            complete_dation_request(target)
            return
        new_status = mapping.get(instance.status)
        if new_status:
            target.status = new_status
            target.save(update_fields=["status", "updated_at"])
        return


def _apply_proposed_amount(instance, proposed_amount):
    target = instance.target
    if target is not None and hasattr(target, "amount_proposed"):
        target.amount_proposed = proposed_amount
        update_fields = ["amount_proposed"]
        if hasattr(target, "updated_at"):
            update_fields.append("updated_at")
        target.save(update_fields=update_fields)


def user_can_act(user, step):
    """Indique si l'utilisateur est habilité à décider sur cette étape.

    Prend en compte les délégations actives : le délégataire peut agir si
    le délégant appartient au groupe requis par l'étape.
    """
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser or getattr(user, "is_group_level", False):
        return True
    if step.required_group_id is None:
        return False
    if user.groups.filter(id=step.required_group_id).exists():
        return True

    from apps.accounts.models import Delegation

    today = timezone.now().date()
    return Delegation.objects.filter(
        delegate_id=user.id,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        delegator__groups__id=step.required_group_id,
    ).exists()


def cancel_active_workflows_for_target(target) -> int:
    """Annule les circuits en cours d'une cible et ignore les tâches PENDING.

    Retourne le nombre d'instances annulées.
    """
    content_type = ContentType.objects.get_for_model(target.__class__)
    instances = list(
        WorkflowInstance.all_tenants.filter(
            content_type=content_type,
            object_id=target.pk,
            status__in=[
                WorkflowInstance.Status.IN_PROGRESS,
                WorkflowInstance.Status.AWAITING_CONDITIONS,
            ],
        )
    )
    for instance in instances:
        instance.tasks.filter(status=ApprovalTask.Status.PENDING).update(
            status=ApprovalTask.Status.SKIPPED
        )
        instance.status = WorkflowInstance.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])
    return len(instances)


def _check_self_validation(user, application):
    """Interdit au soumissionnaire de valider son propre dossier."""
    if user.is_superuser:
        return
    submitter_id = application.submitted_by_id
    if submitter_id and submitter_id == user.id:
        raise WorkflowError(
            "Vous ne pouvez pas statuer sur un dossier que vous avez soumis."
        )


def _open_tasks_for_order(instance, steps, order):
    now = timezone.now()
    for step in steps:
        if step.order == order:
            ApprovalTask.objects.create(
                instance=instance,
                step=step,
                status=ApprovalTask.Status.PENDING,
                due_at=now + timedelta(hours=step.sla_hours),
            )
    try:
        from apps.notifications.services import schedule_step_notifications

        schedule_step_notifications(instance, order)
    except Exception:  # noqa: BLE001
        # Les notifications ne doivent jamais faire échouer le circuit.
        import logging

        logging.getLogger("finflow").exception(
            "Échec de planification des notifications d'étape"
        )


def _validate_opinion(task, decision, opinion, reserves):
    """Contrôle la cohérence avis / décision / type d'étape."""
    step_kind = task.step.step_kind

    if decision == ApprovalTask.Status.APPROVED:
        if not opinion:
            raise WorkflowError("L'avis est obligatoire pour valider.")
        if opinion == ApprovalTask.Opinion.FAVORABLE_SOUS_RESERVE:
            cleaned = [r.strip() for r in (reserves or []) if r and r.strip()]
            if not cleaned:
                raise WorkflowError(
                    "Les réserves sont obligatoires pour un avis favorable sous réserve."
                )
        if (
            opinion == ApprovalTask.Opinion.DEFAVORABLE
            and step_kind == ApprovalStep.StepKind.DECISIONAL
        ):
            raise WorkflowError(
                "Un avis défavorable à une étape décisionnelle doit conduire "
                "à un rejet ou un renvoi, pas à une validation."
            )
        return opinion

    if decision == ApprovalTask.Status.REJECTED:
        if not opinion:
            return ApprovalTask.Opinion.DEFAVORABLE
        return opinion

    return opinion or ""


def _complete_workflow(instance):
    """Finalise le circuit ou le place en attente de réserves."""
    application = _get_credit_application(instance)
    if application and _pending_conditions_exist(application):
        instance.status = WorkflowInstance.Status.AWAITING_CONDITIONS
        instance.save(update_fields=["status", "updated_at"])
        application.status = application.Status.IN_APPROVAL
        application.save(update_fields=["status", "updated_at"])
        return instance

    instance.status = WorkflowInstance.Status.APPROVED
    instance.save(update_fields=["status", "updated_at"])
    _sync_target_status(instance)
    try:
        from apps.notifications.services import schedule_outcome_notification

        schedule_outcome_notification(instance, "APPROVED")
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger("finflow").exception(
            "Échec de planification de la notification de fin de circuit"
        )
    return instance


def has_pending_conditions(application):
    """Indique si le dossier a des réserves non encore validées."""
    return _pending_conditions_exist(application)


@transaction.atomic
def try_finalize_approval(application):
    """Passe le dossier en approuvé si toutes les réserves sont validées."""
    if _pending_conditions_exist(application):
        return None

    content_type = ContentType.objects.get_for_model(application.__class__)
    instance = (
        WorkflowInstance.all_tenants.filter(
            content_type=content_type,
            object_id=application.pk,
            status=WorkflowInstance.Status.AWAITING_CONDITIONS,
        )
        .order_by("-created_at")
        .first()
    )
    if instance is None:
        return None

    instance.status = WorkflowInstance.Status.APPROVED
    instance.save(update_fields=["status", "updated_at"])
    _sync_target_status(instance)
    try:
        from apps.notifications.services import schedule_outcome_notification

        schedule_outcome_notification(instance, "APPROVED")
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger("finflow").exception(
            "Échec de planification de la notification (finalisation réserves)"
        )
    return instance


@transaction.atomic
def lift_condition(condition, user, comment=""):
    """Marque une réserve comme levée (chargé de dossier)."""
    if condition.status != ApprovalCondition.Status.PENDING:
        raise WorkflowError("Cette réserve n'est pas en attente de levée.")

    application = condition.application
    submitter_id = application.submitted_by_id
    creator_id = application.created_by_id
    allowed = (
        user.is_superuser
        or getattr(user, "is_group_level", False)
        or user.id in {submitter_id, creator_id}
    )
    if not allowed:
        raise WorkflowError(
            "Seul le chargé de dossier peut marquer une réserve comme levée."
        )

    condition.status = ApprovalCondition.Status.LIFTED
    condition.lifted_by = user
    condition.lifted_at = timezone.now()
    condition.lift_comment = comment
    condition.save()
    return condition


@transaction.atomic
def validate_condition(condition, user, comment=""):
    """Valide la levée d'une réserve (émetteur uniquement)."""
    if condition.status != ApprovalCondition.Status.LIFTED:
        raise WorkflowError(
            "Seule une réserve levée peut être validée par son émetteur."
        )

    if not user.is_superuser and condition.issued_by_id != user.id:
        raise WorkflowError(
            "Seul le validateur ayant émis la réserve peut confirmer sa levée."
        )

    condition.status = ApprovalCondition.Status.VALIDATED
    condition.validated_by = user
    condition.validated_at = timezone.now()
    condition.validation_comment = comment
    condition.save()

    try_finalize_approval(condition.application)
    return condition


@transaction.atomic
def return_lift(condition, user, comment=""):
    """Renvoie une levée au chargé de dossier (émetteur non satisfait).

    Permet l'aller-retour : l'émetteur de la réserve peut, au lieu de confirmer,
    demander un complément. La réserve repasse « en attente de levée » et le
    chargé de dossier peut de nouveau commenter puis re-soumettre la levée,
    autant de fois que nécessaire, jusqu'à confirmation finale.
    """
    if condition.status != ApprovalCondition.Status.LIFTED:
        raise WorkflowError(
            "Seule une réserve en attente de confirmation peut être renvoyée."
        )

    if not user.is_superuser and condition.issued_by_id != user.id:
        raise WorkflowError(
            "Seul le validateur ayant émis la réserve peut renvoyer la levée."
        )

    condition.status = ApprovalCondition.Status.PENDING
    # On conserve la demande de complément de l'émetteur pour le chargé de dossier
    # et on réinitialise la levée précédente (à refaire).
    condition.validation_comment = comment
    condition.validated_by = None
    condition.validated_at = None
    condition.lifted_by = None
    condition.lifted_at = None
    condition.lift_comment = ""
    condition.save()
    return condition


@transaction.atomic
def process_decision(
    task,
    user,
    decision,
    comment="",
    reject_reason=None,
    proposed_amount=None,
    opinion=None,
    reserves=None,
    return_to_submitter=False,
):
    """Traite une décision sur une tâche d'approbation."""
    task = (
        ApprovalTask.objects.select_for_update()
        .select_related("instance", "step", "instance__definition")
        .get(pk=task.pk)
    )

    if task.status != ApprovalTask.Status.PENDING:
        raise WorkflowError("Cette tâche a déjà été traitée.")

    instance = task.instance
    if instance.status not in (
        WorkflowInstance.Status.IN_PROGRESS,
        WorkflowInstance.Status.AWAITING_CONDITIONS,
    ):
        raise WorkflowError("Le circuit n'est plus en cours.")

    if not user_can_act(user, task.step):
        raise WorkflowError(
            "Vous n'êtes pas habilité à statuer sur cette étape."
        )

    application = _get_credit_application(instance)
    if application:
        _check_self_validation(user, application)

    validated_opinion = _validate_opinion(task, decision, opinion, reserves)

    task.acted_by = user
    task.acted_at = timezone.now()
    task.decision_comment = comment
    if validated_opinion:
        task.opinion = validated_opinion

    if decision == ApprovalTask.Status.REJECTED:
        if not comment.strip():
            raise WorkflowError(
                "Un commentaire détaillé est requis pour rejeter le dossier."
            )
        task.status = ApprovalTask.Status.REJECTED
        task.reject_reason = reject_reason
        task.save()
        instance.status = WorkflowInstance.Status.REJECTED
        instance.save(update_fields=["status", "updated_at"])
        _sync_target_status(instance)
        try:
            from apps.notifications.services import schedule_outcome_notification

            schedule_outcome_notification(instance, "REJECTED")
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger("finflow").exception(
                "Échec de planification de la notification de rejet"
            )
        return instance

    if decision == ApprovalTask.Status.RETURNED:
        if not comment.strip():
            raise WorkflowError(
                "Un commentaire est requis pour renvoyer le dossier."
            )
        if not task.step.allow_return:
            raise WorkflowError("Le retour n'est pas autorisé à cette étape.")
        task.status = ApprovalTask.Status.RETURNED
        task.save()

        from apps.audit.events import (
            RETURNED_STEP,
            RETURNED_SUBMITTER,
            log_workflow_event,
        )

        steps = _applicable_steps(
            instance.definition, instance.amount, instance.risk_level
        )
        prev_orders = sorted(
            {s.order for s in steps if s.order < instance.current_order}
        )
        # Renvoi direct au soumissionnaire : à la demande du validateur, ou
        # faute d'étape inférieure (on est déjà à la première étape).
        if return_to_submitter or not prev_orders:
            instance.tasks.filter(
                status=ApprovalTask.Status.PENDING,
            ).update(status=ApprovalTask.Status.SKIPPED)
            instance.status = WorkflowInstance.Status.RETURNED
            instance.save(update_fields=["status", "updated_at"])
            _sync_target_status(instance)
            if application:
                log_workflow_event(
                    application, RETURNED_SUBMITTER, detail=comment, user=user
                )
            try:
                from apps.notifications.services import schedule_outcome_notification

                schedule_outcome_notification(instance, "RETURNED")
            except Exception:  # noqa: BLE001
                import logging

                logging.getLogger("finflow").exception(
                    "Échec de planification de la notification de renvoi"
                )
        else:
            instance.tasks.filter(
                step__order=instance.current_order,
                status=ApprovalTask.Status.PENDING,
            ).update(status=ApprovalTask.Status.SKIPPED)
            previous_order = prev_orders[-1]
            instance.current_order = previous_order
            instance.save(update_fields=["current_order", "updated_at"])
            _open_tasks_for_order(instance, steps, previous_order)
            if application:
                log_workflow_event(
                    application,
                    RETURNED_STEP,
                    detail=f"Renvoi à l'étape {previous_order}. {comment}".strip(),
                    user=user,
                )
        return instance

    if decision != ApprovalTask.Status.APPROVED:
        raise WorkflowError("Décision inconnue.")

    task.status = ApprovalTask.Status.APPROVED
    if proposed_amount is not None:
        task.proposed_amount = proposed_amount
        _apply_proposed_amount(instance, proposed_amount)
    task.save()

    if (
        validated_opinion == ApprovalTask.Opinion.FAVORABLE_SOUS_RESERVE
        and application
    ):
        cleaned = [r.strip() for r in (reserves or []) if r and r.strip()]
        _create_conditions(task, application, user, cleaned)

    current_tasks = instance.tasks.filter(step__order=instance.current_order)
    if current_tasks.filter(status=ApprovalTask.Status.PENDING).exists():
        return instance

    steps = _applicable_steps(
        instance.definition, instance.amount, instance.risk_level
    )
    next_orders = sorted(
        {s.order for s in steps if s.order > instance.current_order}
    )
    if next_orders:
        instance.current_order = next_orders[0]
        instance.save(update_fields=["current_order", "updated_at"])
        _open_tasks_for_order(instance, steps, next_orders[0])
    else:
        _complete_workflow(instance)
    return instance
