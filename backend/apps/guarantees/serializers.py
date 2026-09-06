import json

from rest_framework import serializers

from .models import (
    Guarantee,
    GuaranteeDocument,
    GuaranteeFormalizationRequest,
    GuaranteeJewelryItem,
    GuaranteeMovement,
    GuaranteePhoto,
    GuaranteeReleaseRequest,
    ReleaseFee,
    DationAsset,
    DationFee,
    DationRequest,
    FormalizationFee,
)


class GuaranteeMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )

    class Meta:
        model = GuaranteeMovement
        fields = [
            "id", "guarantee", "movement_type", "movement_type_display",
            "movement_date", "value", "target_application", "comment",
        ]
        read_only_fields = ["id", "movement_type_display"]


class GuaranteePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteePhoto
        fields = ["id", "image", "caption"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.common.storage_urls import file_download_url

        data["image"] = file_download_url(instance.image)
        return data


class GuaranteeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteeDocument
        fields = ["id", "title", "file", "created_at"]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.common.storage_urls import file_download_url

        data["file"] = file_download_url(instance.file)
        return data


class GuaranteeJewelryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteeJewelryItem
        fields = ["id", "nature", "weight", "description"]
        read_only_fields = ["id"]


class JewelryItemsField(serializers.Field):
    """Accepte une liste de bijoux (JSON) transmise via multipart ou JSON."""

    def to_representation(self, value):
        return GuaranteeJewelryItemSerializer(value.all(), many=True).data

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip()
            if not data:
                return []
            try:
                data = json.loads(data)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError(
                    "Format des bijoux invalide."
                ) from exc
        if not isinstance(data, list):
            raise serializers.ValidationError("Une liste de bijoux est attendue.")
        items = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            nature = str(raw.get("nature") or "").strip()
            desc = str(raw.get("description") or "").strip()
            weight_raw = raw.get("weight")
            if not (nature or desc or weight_raw not in (None, "")):
                continue
            weight = None
            if weight_raw not in (None, ""):
                try:
                    weight = float(weight_raw)
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError(
                        f"Poids invalide pour « {nature or 'bijou'} »."
                    ) from exc
            items.append(
                {"nature": nature, "weight": weight, "description": desc}
            )
        return items


class GuaranteeListSerializer(serializers.ModelSerializer):
    """Liste allégée — sans mouvements, photos ni scans."""

    type_display = serializers.CharField(
        source="get_guarantee_type_display", read_only=True
    )
    renewed_from_reference = serializers.CharField(
        source="renewed_from.reference", read_only=True, default=None
    )
    surety_display = serializers.SerializerMethodField()
    open_formalization_id = serializers.SerializerMethodField()

    class Meta:
        model = Guarantee
        fields = [
            "id", "reference", "guarantee_type", "type_display", "agency",
            "pledge_category", "client", "application",
            "belongs_to_applicant", "surety", "surety_display",
            "current_value", "ltv_ratio", "status",
            "registration_number", "registration_date",
            "registration_authority", "formalized_at",
            "open_formalization_id",
            "renewed_from_reference", "created_at",
        ]
        read_only_fields = fields

    def get_surety_display(self, obj) -> str | None:
        if not obj.surety_id:
            return None
        return getattr(obj.surety, "display_name", None) or str(obj.surety)

    def get_open_formalization_id(self, obj):
        open_statuses = (
            GuaranteeFormalizationRequest.Status.DRAFT,
            GuaranteeFormalizationRequest.Status.IN_PROGRESS,
            GuaranteeFormalizationRequest.Status.IN_APPROVAL,
            GuaranteeFormalizationRequest.Status.RETURNED,
            GuaranteeFormalizationRequest.Status.APPROVED,
        )
        req = (
            obj.formalization_requests.filter(status__in=open_statuses)
            .order_by("-created_at")
            .only("id")
            .first()
        )
        return str(req.id) if req else None


class GuaranteeSerializer(serializers.ModelSerializer):
    movements = GuaranteeMovementSerializer(many=True, read_only=True)
    photos = GuaranteePhotoSerializer(many=True, read_only=True)
    documents = GuaranteeDocumentSerializer(many=True, read_only=True)
    jewelry_items = JewelryItemsField(required=False)
    type_display = serializers.CharField(
        source="get_guarantee_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    renewed_from_reference = serializers.CharField(
        source="renewed_from.reference", read_only=True, default=None
    )
    surety_display = serializers.SerializerMethodField()
    client_display = serializers.SerializerMethodField()
    application_reference = serializers.SerializerMethodField()
    agency_name = serializers.SerializerMethodField()
    open_formalization_id = serializers.SerializerMethodField()

    class Meta:
        model = Guarantee
        fields = [
            "id", "reference", "guarantee_type", "type_display", "agency",
            "agency_name",
            "pledge_category", "client", "client_display",
            "application", "application_reference",
            "belongs_to_applicant", "surety", "surety_display",
            "description", "owners", "expertise_value", "current_value",
            "is_insured", "insurance_reference",
            # Propriétaire
            "owner_last_name", "owner_first_name", "owner_marital_status",
            "matrimonial_regime",
            # Hypothèque
            "document_type", "document_number", "document_issue_date",
            "address", "expertise_date", "expertise_firm", "expert_name",
            "value_to_consider",
            "ltv_ratio", "occupancy_status", "document_scan",
            "expertise_report_scan", "lease_contract_scan",
            "legal_situation_certificate_scan",
            # Gage — moyen roulant
            "chassis_number", "engine_number", "brand", "model_name",
            "registration", "power", "first_registration_year",
            "acquisition_date", "acquisition_value", "resale_value",
            "estimation_date", "registration_card_scan",
            "mechanical_expertise_scan", "technical_inspection_scan",
            "insurance_scan", "purchase_invoice_scan", "additional_info",
            # Gage — objet de valeur
            "raw_material_price", "expertise_certificate_scan",
            "origin_certificate_scan",
            # Garantie financière
            "financial_type", "account_number", "balance", "remuneration_rate",
            "deposit_maturity_date", "isin_code", "volatility_history",
            "security_discount", "pledge_deed_scan",
            # Suivi
            "status", "status_display", "last_valuation_date",
            "photos", "documents",
            "movements",
            "jewelry_items", "renewed_from", "renewed_from_reference",
            "registration_number", "registration_date",
            "registration_authority", "formalized_at",
            "open_formalization_id",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "status_display", "current_value", "ltv_ratio",
            "renewed_from", "renewed_from_reference", "surety_display",
            "client_display", "application_reference", "agency_name",
            "registration_number", "registration_date",
            "registration_authority", "formalized_at",
            "open_formalization_id",
            "created_at", "updated_at",
        ]

    def get_surety_display(self, obj) -> str | None:
        if not obj.surety_id:
            return None
        return getattr(obj.surety, "display_name", None) or str(obj.surety)

    def get_client_display(self, obj) -> str | None:
        if not obj.client_id:
            return None
        return getattr(obj.client, "display_name", None) or str(obj.client)

    def get_application_reference(self, obj) -> str | None:
        if not obj.application_id:
            return None
        return obj.application.reference or str(obj.application_id)

    def get_agency_name(self, obj) -> str | None:
        if not obj.agency_id:
            return None
        return obj.agency.name

    def get_open_formalization_id(self, obj):
        open_statuses = (
            GuaranteeFormalizationRequest.Status.DRAFT,
            GuaranteeFormalizationRequest.Status.IN_PROGRESS,
            GuaranteeFormalizationRequest.Status.IN_APPROVAL,
            GuaranteeFormalizationRequest.Status.RETURNED,
            GuaranteeFormalizationRequest.Status.APPROVED,
        )
        req = (
            obj.formalization_requests.filter(status__in=open_statuses)
            .order_by("-created_at")
            .only("id")
            .first()
        )
        return str(req.id) if req else None

    def validate(self, attrs):
        belongs = attrs.get(
            "belongs_to_applicant",
            getattr(self.instance, "belongs_to_applicant", True),
        )
        # multipart envoie souvent "true"/"false" déjà coercés en bool par DRF
        if isinstance(belongs, str):
            belongs = belongs.strip().lower() in ("1", "true", "yes", "oui")
            attrs["belongs_to_applicant"] = belongs

        surety = attrs.get(
            "surety",
            getattr(self.instance, "surety", None) if self.instance else None,
        )
        if "surety" in attrs and attrs["surety"] == "":
            surety = None
            attrs["surety"] = None

        if belongs:
            attrs["surety"] = None
        elif not surety:
            raise serializers.ValidationError({
                "surety": (
                    "Indiquez la caution : le bien n'appartient pas au "
                    "client demandeur."
                ),
            })
        return attrs

    def _save_photos(self, guarantee):
        request = self.context.get("request")
        if not request:
            return
        for image in request.FILES.getlist("photos"):
            GuaranteePhoto.objects.create(
                guarantee=guarantee,
                tenant_id=guarantee.tenant_id,
                image=image,
            )

    def _save_documents(self, guarantee):
        """Ajoute des documents (titles + files) et supprime ceux demandés."""
        request = self.context.get("request")
        if not request:
            return

        raw_delete = request.data.get("delete_document_ids") or "[]"
        if isinstance(raw_delete, str):
            try:
                delete_ids = json.loads(raw_delete or "[]")
            except json.JSONDecodeError:
                delete_ids = []
        else:
            delete_ids = list(raw_delete) if raw_delete else []
        if delete_ids:
            guarantee.documents.filter(id__in=delete_ids).delete()

        titles = request.data.getlist("document_titles") if hasattr(
            request.data, "getlist"
        ) else request.data.get("document_titles") or []
        if isinstance(titles, str):
            try:
                titles = json.loads(titles or "[]")
            except json.JSONDecodeError:
                titles = [titles] if titles.strip() else []
        files = request.FILES.getlist("documents")
        for idx, uploaded in enumerate(files):
            title = ""
            if idx < len(titles):
                title = str(titles[idx] or "").strip()
            if not title:
                title = getattr(uploaded, "name", None) or f"Document {idx + 1}"
            GuaranteeDocument.objects.create(
                guarantee=guarantee,
                tenant_id=guarantee.tenant_id,
                title=title[:200],
                file=uploaded,
            )

    def _save_jewelry_items(self, guarantee, items):
        """Remplace l'ensemble des composantes de bijou de la garantie."""
        if items is None:
            return
        guarantee.jewelry_items.all().delete()
        for item in items:
            GuaranteeJewelryItem.objects.create(
                guarantee=guarantee,
                tenant_id=guarantee.tenant_id,
                **item,
            )

    def create(self, validated_data):
        jewelry_items = validated_data.pop("jewelry_items", None)
        guarantee = super().create(validated_data)
        self._save_photos(guarantee)
        self._save_documents(guarantee)
        self._save_jewelry_items(guarantee, jewelry_items)
        return guarantee

    def update(self, instance, validated_data):
        jewelry_items = validated_data.pop("jewelry_items", None)
        guarantee = super().update(instance, validated_data)
        self._save_photos(guarantee)
        self._save_documents(guarantee)
        self._save_jewelry_items(guarantee, jewelry_items)
        return guarantee


class ReleaseFeeSerializer(serializers.ModelSerializer):
    fee_type_display = serializers.CharField(
        source="get_fee_type_display", read_only=True
    )
    payer_display = serializers.CharField(
        source="get_payer_display", read_only=True
    )

    class Meta:
        model = ReleaseFee
        fields = [
            "id",
            "fee_type",
            "fee_type_display",
            "label",
            "amount",
            "payer",
            "payer_display",
            "fee_date",
            "recoverable",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class ReleaseDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Code GED (ex. ML_DEMANDE). Défaut : ML_OTHER.",
    )


class GuaranteeReleaseRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    acte_status_display = serializers.CharField(
        source="get_acte_status_display", read_only=True
    )
    guarantee_reference = serializers.CharField(
        source="guarantee.reference", read_only=True
    )
    client_display = serializers.SerializerMethodField()
    fees = ReleaseFeeSerializer(many=True, read_only=True)
    has_client_demande = serializers.SerializerMethodField()
    has_generated_acte = serializers.SerializerMethodField()
    has_signed_acte = serializers.SerializerMethodField()
    can_deposit_signed_acte = serializers.SerializerMethodField()
    acte_generated_url = serializers.SerializerMethodField()
    acte_signed_url = serializers.SerializerMethodField()

    class Meta:
        model = GuaranteeReleaseRequest
        fields = [
            "id",
            "reference",
            "guarantee",
            "guarantee_reference",
            "application",
            "loan",
            "agency",
            "cbs_loan_reference",
            "cbs_client_id",
            "cbs_settled",
            "cbs_outstanding",
            "cbs_currency",
            "cbs_checked_at",
            "cbs_raw",
            "request_date",
            "release_fees",
            "fees",
            "fees_client_total",
            "fees_institution_total",
            "acte_status",
            "acte_status_display",
            "acte_generated_at",
            "acte_signed_at",
            "acte_generated_url",
            "acte_signed_url",
            "has_client_demande",
            "has_generated_acte",
            "has_signed_acte",
            "can_deposit_signed_acte",
            "status",
            "status_display",
            "comment",
            "completed_at",
            "client_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "cbs_settled",
            "cbs_outstanding",
            "cbs_currency",
            "cbs_checked_at",
            "cbs_raw",
            "fees",
            "fees_client_total",
            "fees_institution_total",
            "acte_status",
            "acte_status_display",
            "acte_generated_at",
            "acte_signed_at",
            "acte_generated_url",
            "acte_signed_url",
            "has_client_demande",
            "has_generated_acte",
            "has_signed_acte",
            "can_deposit_signed_acte",
            "status",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_client_display(self, obj):
        client = obj.guarantee.client if obj.guarantee_id else None
        return getattr(client, "display_name", str(client)) if client else ""

    def get_has_client_demande(self, obj):
        from apps.guarantees.process_services import has_client_demande

        return has_client_demande(obj)

    def get_has_generated_acte(self, obj):
        return obj.has_generated_acte()

    def get_has_signed_acte(self, obj):
        return obj.has_signed_acte()

    def get_can_deposit_signed_acte(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        from apps.guarantees.process_services import user_can_deposit_release_acte

        return user_can_deposit_release_acte(user, obj)

    def get_acte_generated_url(self, obj):
        if not obj.acte_generated:
            return None
        from apps.common.storage_urls import file_download_url

        return file_download_url(obj.acte_generated)

    def get_acte_signed_url(self, obj):
        if not obj.acte_signed:
            return None
        from apps.common.storage_urls import file_download_url

        return file_download_url(obj.acte_signed)


class DationAssetSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(
        source="get_source_display", read_only=True
    )
    asset_type_display = serializers.CharField(
        source="get_asset_type_display", read_only=True
    )
    guarantee_reference = serializers.CharField(
        source="guarantee.reference", read_only=True, default=None
    )
    guarantee_type_display = serializers.CharField(
        source="guarantee.get_guarantee_type_display",
        read_only=True,
        default=None,
    )

    class Meta:
        model = DationAsset
        fields = [
            "id",
            "source",
            "source_display",
            "asset_type",
            "asset_type_display",
            "guarantee",
            "guarantee_reference",
            "guarantee_type_display",
            "description",
            "value",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class DationFeeSerializer(serializers.ModelSerializer):
    fee_type_display = serializers.CharField(
        source="get_fee_type_display", read_only=True
    )
    payer_display = serializers.CharField(
        source="get_payer_display", read_only=True
    )

    class Meta:
        model = DationFee
        fields = [
            "id",
            "asset",
            "fee_type",
            "fee_type_display",
            "label",
            "amount",
            "payer",
            "payer_display",
            "fee_date",
            "recoverable",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class DationDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Code catégorie GED (ex. DAT_PHOTO). Défaut : DAT_OTHER.",
    )
    asset = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optionnel : rattacher la pièce à un bien du dossier.",
    )


class DationRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    client_display = serializers.SerializerMethodField()
    assets = DationAssetSerializer(many=True, read_only=True)
    fees = DationFeeSerializer(many=True, read_only=True)
    assets_total_value = serializers.SerializerMethodField()
    covers_claim = serializers.SerializerMethodField()
    coverage_gap = serializers.SerializerMethodField()
    settlement = serializers.SerializerMethodField()

    class Meta:
        model = DationRequest
        fields = [
            "id",
            "reference",
            "client",
            "client_display",
            "application",
            "agency",
            "cbs_client_id",
            "cbs_total_outstanding",
            "cbs_currency",
            "cbs_checked_at",
            "cbs_raw",
            "asset_description",
            "asset_value",
            "assets",
            "fees",
            "assets_total_value",
            "fees_client_total",
            "fees_institution_total",
            "claim_to_cover",
            "residual_balance",
            "surplus_amount",
            "require_full_coverage",
            "settlement_notes",
            "covers_claim",
            "coverage_gap",
            "settlement",
            "status",
            "status_display",
            "comment",
            "resulting_guarantee",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "cbs_total_outstanding",
            "cbs_currency",
            "cbs_checked_at",
            "cbs_raw",
            "status",
            "resulting_guarantee",
            "completed_at",
            "created_at",
            "updated_at",
            "assets",
            "fees",
            "assets_total_value",
            "fees_client_total",
            "fees_institution_total",
            "claim_to_cover",
            "residual_balance",
            "surplus_amount",
            "covers_claim",
            "coverage_gap",
            "settlement",
        ]

    def get_client_display(self, obj):
        client = obj.client
        return getattr(client, "display_name", str(client)) if client else ""

    def get_assets_total_value(self, obj):
        return obj.assets_total_value()

    def get_covers_claim(self, obj):
        return obj.covers_claim()

    def get_coverage_gap(self, obj):
        data = obj.compute_settlement()
        if obj.cbs_total_outstanding is None:
            return None
        return data["coverage_gap"]

    def get_settlement(self, obj):
        data = obj.compute_settlement()
        return {k: (str(v) if hasattr(v, "quantize") else v) for k, v in data.items()}


class FormalizationFeeSerializer(serializers.ModelSerializer):
    fee_type_display = serializers.CharField(
        source="get_fee_type_display", read_only=True
    )
    payer_display = serializers.CharField(
        source="get_payer_display", read_only=True
    )

    class Meta:
        model = FormalizationFee
        fields = [
            "id",
            "fee_type",
            "fee_type_display",
            "label",
            "amount",
            "payer",
            "payer_display",
            "fee_date",
            "recoverable",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class FormalizationDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Code GED (ex. FORM_ACTE_SIGNE). Défaut : FORM_OTHER.",
    )


class GuaranteeFormalizationRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    legal_stage_display = serializers.CharField(
        source="get_legal_stage_display", read_only=True
    )
    client_display = serializers.SerializerMethodField()
    guarantee_reference = serializers.CharField(
        source="guarantee.reference", read_only=True, default=None
    )
    fees = FormalizationFeeSerializer(many=True, read_only=True)
    acte_file_url = serializers.SerializerMethodField()
    acte_signed_file_url = serializers.SerializerMethodField()
    registration_proof_url = serializers.SerializerMethodField()

    class Meta:
        model = GuaranteeFormalizationRequest
        fields = [
            "id",
            "reference",
            "guarantee",
            "guarantee_reference",
            "application",
            "agency",
            "status",
            "status_display",
            "legal_stage",
            "legal_stage_display",
            "notary_name",
            "notary_reference",
            "sent_to_notary_at",
            "expected_return_date",
            "registration_number",
            "registration_date",
            "registration_authority",
            "acte_file",
            "acte_file_url",
            "acte_signed_file",
            "acte_signed_file_url",
            "registration_proof",
            "registration_proof_url",
            "fees",
            "fees_client_total",
            "fees_institution_total",
            "comment",
            "client_display",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "status",
            "status_display",
            "legal_stage_display",
            "fees",
            "fees_client_total",
            "fees_institution_total",
            "acte_file_url",
            "acte_signed_file_url",
            "registration_proof_url",
            "client_display",
            "guarantee_reference",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_client_display(self, obj):
        client = obj.guarantee.client if obj.guarantee_id else None
        return getattr(client, "display_name", str(client)) if client else ""

    def get_acte_file_url(self, obj):
        if not obj.acte_file:
            return None
        from apps.common.storage_urls import file_download_url

        return file_download_url(obj.acte_file)

    def get_acte_signed_file_url(self, obj):
        if not obj.acte_signed_file:
            return None
        from apps.common.storage_urls import file_download_url

        return file_download_url(obj.acte_signed_file)

    def get_registration_proof_url(self, obj):
        if not obj.registration_proof:
            return None
        from apps.common.storage_urls import file_download_url

        return file_download_url(obj.registration_proof)
