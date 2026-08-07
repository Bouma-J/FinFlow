from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from apps.common.tenancy import get_current_tenant_id
from apps.tenants.models import Agency

from .models import DataScope, Delegation, TenantRole, User
from .services import create_tenant_role, validate_groups_for_tenant


class PermissionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    app_label = serializers.CharField(
        source="content_type.app_label", read_only=True
    )
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "app_label", "model", "label"]

    def get_label(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"


class GroupSerializer(serializers.ModelSerializer):
    """Sérialiseur legacy — préférer TenantRoleSerializer."""

    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    permissions_detail = PermissionSerializer(
        source="permissions", many=True, read_only=True
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "permissions_detail", "user_count"]

    def get_user_count(self, obj):
        return obj.user_set.count()


class TenantRoleSerializer(serializers.ModelSerializer):
    """Rôle filiale exposé via l'API /roles/."""

    id = serializers.IntegerField(source="group.id", read_only=True)
    tenant = serializers.UUIDField(source="tenant_id", read_only=True)
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        source="group.permissions",
        required=False,
    )
    permissions_detail = PermissionSerializer(
        source="group.permissions", many=True, read_only=True
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = TenantRole
        fields = [
            "id", "tenant", "name", "permissions", "permissions_detail",
            "user_count", "created_at",
        ]
        read_only_fields = ["id", "tenant", "created_at"]

    def get_user_count(self, obj):
        return obj.group.user_set.count()

    def create(self, validated_data):
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError(
                "Aucune filiale sélectionnée. Choisissez une filiale avant "
                "de créer un rôle."
            )
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        group_data = validated_data.pop("group", {})
        permissions = group_data.get("permissions", [])
        name = validated_data["name"]
        if TenantRole.objects.filter(tenant=tenant, name=name).exists():
            raise serializers.ValidationError(
                {"name": "Un rôle avec ce nom existe déjà pour cette filiale."}
            )
        return create_tenant_role(tenant, name, permissions)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.name = validated_data["name"]
            instance.save(update_fields=["name"])
        group_data = validated_data.get("group", {})
        if "permissions" in group_data:
            instance.group.permissions.set(group_data["permissions"])
        return instance


class UserGroupSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name"]

    def get_name(self, obj):
        tr = getattr(obj, "tenant_role", None)
        return tr.name if tr else obj.name


class AgencySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = ["id", "code", "name"]


class UserSerializer(serializers.ModelSerializer):
    groups = UserGroupSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), source="groups",
        write_only=True, required=False,
    )
    agencies_detail = AgencySummarySerializer(
        source="agencies", many=True, read_only=True
    )
    agency_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Agency.objects.all(),
        source="agencies",
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "tenant", "agency", "agencies_detail", "agency_ids",
            "data_scope", "is_group_level", "is_staff", "employee_id",
            "phone", "mfa_enabled", "must_change_password", "is_active",
            "groups", "group_ids",
            "date_joined", "last_login",
        ]
        read_only_fields = [
            "id", "date_joined", "last_login", "is_staff", "must_change_password",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        # Seul un admin Groupe peut élever/révoquer is_staff sur un user filiale
        if user and (
            getattr(user, "is_group_level", False) or user.is_superuser
        ):
            self.fields["is_staff"].read_only = False

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None) if request else None
        if "is_staff" in attrs:
            if not (
                actor
                and (
                    getattr(actor, "is_group_level", False)
                    or actor.is_superuser
                )
            ):
                raise serializers.ValidationError({
                    "is_staff": "Seul un administrateur Groupe peut modifier ce droit."
                })
            # Interdit d'élever un user Groupe via ce champ hors provision dédiée
            target = self.instance
            is_group = attrs.get(
                "is_group_level",
                getattr(target, "is_group_level", False) if target else False,
            )
            if is_group and not attrs.get("is_staff", True):
                pass  # autoriser désactivation staff groupe
        return self._validate_user_scope(attrs)

    def _validate_user_scope(self, attrs):
        is_group = attrs.get(
            "is_group_level",
            getattr(self.instance, "is_group_level", False),
        )
        tenant = attrs.get("tenant", getattr(self.instance, "tenant", None))
        agency = attrs.get("agency", getattr(self.instance, "agency", None))
        agencies = attrs.get("agencies")

        if not is_group:
            if agency is None:
                raise serializers.ValidationError({
                    "agency": "L'agence principale est obligatoire."
                })
            if tenant and agency.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    "agency": "L'agence doit appartenir à la filiale."
                })
            if agencies:
                for ag in agencies:
                    if tenant and ag.tenant_id != tenant.id:
                        raise serializers.ValidationError({
                            "agency_ids": "Toutes les agences doivent appartenir à la filiale."
                        })
        return attrs

    def create(self, validated_data):
        agencies = validated_data.pop("agencies", None)
        user = super().create(validated_data)
        if agencies is not None:
            user.agencies.set(agencies)
        elif user.agency_id:
            user.agencies.add(user.agency)
        return user

    def update(self, instance, validated_data):
        agencies = validated_data.pop("agencies", None)
        user = super().update(instance, validated_data)
        if agencies is not None:
            user.agencies.set(agencies)
            if user.agency_id and not user.agencies.filter(pk=user.agency_id).exists():
                user.agencies.add(user.agency)
        return user


class UserCreateSerializer(serializers.ModelSerializer):
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), source="groups",
        write_only=True, required=False,
    )
    agency_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Agency.objects.all(),
        source="agencies",
        write_only=True,
        required=False,
    )
    as_filiale_admin = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        help_text=(
            "Si vrai (admin Groupe uniquement) : crée un administrateur "
            "filiale (is_staff, périmètre TENANT, rôle Administrateur filiale)."
        ),
    )
    password_delivery = serializers.ChoiceField(
        choices=["email", "manual"],
        required=False,
        default="email",
        write_only=True,
        help_text="email = générer et envoyer ; manual = mot de passe saisi.",
    )
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )
    email_sent = serializers.SerializerMethodField(read_only=True)
    password_delivery_mode = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "tenant", "agency", "agency_ids", "data_scope",
            "is_group_level", "employee_id", "phone",
            "is_active", "group_ids", "as_filiale_admin",
            "password_delivery", "password", "password_confirm",
            "email_sent", "password_delivery_mode",
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
        }

    def get_email_sent(self, obj):
        return bool(getattr(obj, "_email_sent", False))

    def get_password_delivery_mode(self, obj):
        return getattr(obj, "_password_delivery", "email")

    def validate(self, attrs):
        from .password_services import validate_password_delivery

        as_admin = attrs.pop("as_filiale_admin", False)
        request = self.context.get("request")
        actor = getattr(request, "user", None) if request else None

        attrs = validate_password_delivery(attrs, email_field="email")

        if as_admin:
            if not (
                actor
                and (
                    getattr(actor, "is_group_level", False)
                    or actor.is_superuser
                )
            ):
                raise serializers.ValidationError({
                    "as_filiale_admin": (
                        "Seul un administrateur Groupe peut provisionner "
                        "un admin filiale."
                    )
                })
            if attrs.get("is_group_level"):
                raise serializers.ValidationError({
                    "as_filiale_admin": (
                        "Un admin filiale ne peut pas être un utilisateur Groupe."
                    )
                })
            attrs["_as_filiale_admin"] = True

        is_group = attrs.get("is_group_level", False)
        tenant = attrs.get("tenant")
        tenant_id = get_current_tenant_id()

        if not is_group:
            if tenant is None:
                if tenant_id:
                    from apps.tenants.models import Tenant
                    attrs["tenant"] = Tenant.objects.get(pk=tenant_id)
                else:
                    raise serializers.ValidationError({
                        "tenant": "La filiale est obligatoire pour un utilisateur filiale."
                    })
            agency = attrs.get("agency")
            if agency is None:
                raise serializers.ValidationError({
                    "agency": "L'agence principale est obligatoire."
                })
            if agency.tenant_id != attrs["tenant"].id:
                raise serializers.ValidationError({
                    "agency": "L'agence doit appartenir à la filiale."
                })
            agencies = attrs.get("agencies", [])
            if agencies:
                for ag in agencies:
                    if ag.tenant_id != attrs["tenant"].id:
                        raise serializers.ValidationError({
                            "agency_ids": "Toutes les agences doivent appartenir à la filiale."
                        })
            else:
                attrs["agencies"] = [agency]
            groups = attrs.get("groups", [])
            if groups and not as_admin:
                try:
                    validate_groups_for_tenant(attrs["tenant"].id, groups)
                except ValueError as exc:
                    raise serializers.ValidationError({"group_ids": str(exc)})
        elif tenant is not None:
            raise serializers.ValidationError({
                "tenant": "Un utilisateur Groupe ne doit pas être rattaché à une filiale."
            })
        else:
            attrs["data_scope"] = DataScope.TENANT
        return attrs

    def create(self, validated_data):
        from .password_services import (
            PASSWORD_DELIVERY_EMAIL,
            assign_password,
            issue_temporary_password,
        )

        as_admin = validated_data.pop("_as_filiale_admin", False)
        groups = validated_data.pop("groups", [])
        agencies = validated_data.pop("agencies", [])
        delivery = validated_data.pop("password_delivery", PASSWORD_DELIVERY_EMAIL)
        raw_password = validated_data.pop("password", None) or None
        validated_data.pop("password_confirm", None)

        if as_admin:
            from .services import provision_filiale_admin

            send_mail = delivery == PASSWORD_DELIVERY_EMAIL
            user, _ = provision_filiale_admin(
                tenant=validated_data["tenant"],
                agency=validated_data["agency"],
                username=validated_data["username"],
                password=None if send_mail else raw_password,
                email=validated_data.get("email", ""),
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                phone=validated_data.get("phone", ""),
                employee_id=validated_data.get("employee_id", ""),
                agency_ids=agencies,
                send_credentials=send_mail,
                must_change_password=True,
            )
            if groups:
                try:
                    validate_groups_for_tenant(user.tenant_id, groups)
                except ValueError as exc:
                    raise serializers.ValidationError({"group_ids": str(exc)})
                user.groups.add(*groups)
            user._password_delivery = delivery  # noqa: SLF001
            return user

        validated_data["must_change_password"] = True
        user = User(**validated_data)
        user.set_unusable_password()
        user.full_clean()
        user.save()
        if agencies:
            user.agencies.set(agencies)
        elif user.agency_id:
            user.agencies.add(user.agency)
        if groups:
            user.groups.set(groups)

        if delivery == PASSWORD_DELIVERY_EMAIL:
            _, email_sent = issue_temporary_password(
                user, reason="created", send_email=True
            )
            user._email_sent = email_sent  # noqa: SLF001
        else:
            try:
                assign_password(user, raw_password, must_change_password=True)
            except Exception as exc:  # noqa: BLE001 — ValidationError Django
                user.delete()
                raise serializers.ValidationError({
                    "password": list(exc.messages)
                    if hasattr(exc, "messages")
                    else [str(exc)]
                }) from exc
            user._email_sent = False  # noqa: SLF001
        user._password_delivery = delivery  # noqa: SLF001
        return user


class ProvisionFilialeAdminSerializer(serializers.Serializer):
    """Payload dédié : création d'un admin filiale par l'admin Groupe."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=150
    )
    last_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=150
    )
    phone = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=30
    )
    employee_id = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=50
    )
    tenant = serializers.UUIDField(required=False)
    agency = serializers.UUIDField()
    agency_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    password_delivery = serializers.ChoiceField(
        choices=["email", "manual"],
        required=False,
        default="email",
    )
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )

    def validate(self, attrs):
        from apps.tenants.models import Agency, Tenant
        from .password_services import validate_password_delivery

        attrs = validate_password_delivery(attrs, email_field="email")

        tenant_id = attrs.get("tenant") or get_current_tenant_id()
        if not tenant_id:
            raise serializers.ValidationError({
                "tenant": (
                    "Indiquez la filiale (champ tenant ou en-tête X-Tenant-Id)."
                )
            })
        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist as exc:
            raise serializers.ValidationError({
                "tenant": "Filiale introuvable."
            }) from exc

        try:
            agency = Agency.objects.get(pk=attrs["agency"])
        except Agency.DoesNotExist as exc:
            raise serializers.ValidationError({
                "agency": "Agence introuvable."
            }) from exc

        if agency.tenant_id != tenant.id:
            raise serializers.ValidationError({
                "agency": "L'agence doit appartenir à la filiale."
            })

        extra_ids = attrs.get("agency_ids") or []
        agencies = []
        for aid in extra_ids:
            try:
                ag = Agency.objects.get(pk=aid)
            except Agency.DoesNotExist as exc:
                raise serializers.ValidationError({
                    "agency_ids": f"Agence introuvable : {aid}."
                }) from exc
            if ag.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    "agency_ids": "Toutes les agences doivent appartenir à la filiale."
                })
            agencies.append(ag)

        attrs["tenant_obj"] = tenant
        attrs["agency_obj"] = agency
        attrs["agency_objs"] = agencies
        return attrs

    def create(self, validated_data):
        from .password_services import PASSWORD_DELIVERY_EMAIL
        from .services import provision_filiale_admin

        delivery = validated_data.get("password_delivery", PASSWORD_DELIVERY_EMAIL)
        send_mail = delivery == PASSWORD_DELIVERY_EMAIL
        raw_password = validated_data.get("password") or None

        user, created = provision_filiale_admin(
            tenant=validated_data["tenant_obj"],
            agency=validated_data["agency_obj"],
            username=validated_data["username"],
            password=None if send_mail else raw_password,
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
            employee_id=validated_data.get("employee_id", ""),
            agency_ids=validated_data.get("agency_objs") or [],
            send_credentials=send_mail,
            must_change_password=True,
        )
        user._provision_created = created  # noqa: SLF001
        user._password_delivery = delivery  # noqa: SLF001
        return user


class AdminSetPasswordSerializer(serializers.Serializer):
    """Régénération de mot de passe par un administrateur."""

    password_delivery = serializers.ChoiceField(
        choices=["email", "manual"],
        required=False,
        default="email",
    )
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )

    def validate(self, attrs):
        from .password_services import (
            PASSWORD_DELIVERY_EMAIL,
            PASSWORD_DELIVERY_MANUAL,
        )

        delivery = attrs.get("password_delivery") or PASSWORD_DELIVERY_EMAIL
        attrs["password_delivery"] = delivery
        if delivery == PASSWORD_DELIVERY_MANUAL:
            password = attrs.get("password") or ""
            confirm = attrs.get("password_confirm") or ""
            if not password:
                raise serializers.ValidationError({
                    "password": "Indiquez le mot de passe à attribuer."
                })
            if password != confirm:
                raise serializers.ValidationError({
                    "password_confirm": "Les mots de passe ne correspondent pas."
                })
        elif delivery != PASSWORD_DELIVERY_EMAIL:
            raise serializers.ValidationError({
                "password_delivery": "Choix invalide (email ou manual)."
            })
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=10)
    new_password_confirm = serializers.CharField(write_only=True, min_length=10)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({
                "new_password_confirm": "Les mots de passe ne correspondent pas."
            })
        from django.contrib.auth.password_validation import validate_password

        user = self.context["request"].user
        try:
            validate_password(attrs["new_password"], user=user)
        except Exception as exc:  # noqa: BLE001 — ValidationError Django
            raise serializers.ValidationError({
                "new_password": list(exc.messages)
                if hasattr(exc, "messages")
                else [str(exc)]
            }) from exc
        return attrs


class MeSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    tenant_branding = serializers.SerializerMethodField()
    agencies_detail = AgencySummarySerializer(
        source="agencies", many=True, read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "tenant", "agency", "agencies_detail", "data_scope",
            "is_group_level", "is_staff", "is_superuser", "mfa_enabled",
            "must_change_password", "roles", "permissions", "tenant_branding",
        ]

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def get_roles(self, obj):
        names = []
        for group in obj.groups.select_related("tenant_role").all():
            tr = getattr(group, "tenant_role", None)
            names.append(tr.name if tr else group.name)
        return names

    def get_tenant_branding(self, obj):
        from apps.common.storage_urls import tenant_logo_url

        tenant = obj.tenant
        if tenant is None:
            return None
        request = self.context.get("request")
        return {
            "id": str(tenant.id),
            "code": tenant.code,
            "name": tenant.name,
            "logo_url": tenant_logo_url(tenant, request),
            "brand_primary": tenant.brand_primary,
            "brand_secondary": tenant.brand_secondary,
            "brand_accent": tenant.brand_accent,
        }


class DelegationSerializer(serializers.ModelSerializer):
    is_currently_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Delegation
        fields = [
            "id", "delegator", "delegate", "reason",
            "start_date", "end_date", "is_active",
            "is_currently_valid", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
