import json

from rest_framework import serializers

from .models import (
    Guarantee,
    GuaranteeDocument,
    GuaranteeJewelryItem,
    GuaranteeMovement,
    GuaranteePhoto,
    GuaranteeReleaseRequest,
    DationAsset,
    DationRequest,
)


class GuaranteeMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteeMovement
        fields = [
            "id", "guarantee", "movement_type", "movement_date",
            "value", "target_application", "comment",
        ]
        read_only_fields = ["id"]


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

    class Meta:
        model = Guarantee
        fields = [
            "id", "reference", "guarantee_type", "type_display", "agency",
            "pledge_category", "client", "application",
            "belongs_to_applicant", "surety", "surety_display",
            "current_value", "ltv_ratio", "status",
            "renewed_from_reference", "created_at",
        ]
        read_only_fields = fields

    def get_surety_display(self, obj) -> str | None:
        if not obj.surety_id:
            return None
        return getattr(obj.surety, "display_name", None) or str(obj.surety)


class GuaranteeSerializer(serializers.ModelSerializer):
    movements = GuaranteeMovementSerializer(many=True, read_only=True)
    photos = GuaranteePhotoSerializer(many=True, read_only=True)
    documents = GuaranteeDocumentSerializer(many=True, read_only=True)
    jewelry_items = JewelryItemsField(required=False)
    type_display = serializers.CharField(
        source="get_guarantee_type_display", read_only=True
    )
    renewed_from_reference = serializers.CharField(
        source="renewed_from.reference", read_only=True, default=None
    )
    surety_display = serializers.SerializerMethodField()

    class Meta:
        model = Guarantee
        fields = [
            "id", "reference", "guarantee_type", "type_display", "agency",
            "pledge_category", "client", "application",
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
            "status", "last_valuation_date", "photos", "documents",
            "movements",
            "jewelry_items", "renewed_from", "renewed_from_reference",
            "created_at",
        ]
        read_only_fields = [
            "id", "status", "current_value", "ltv_ratio",
            "renewed_from", "renewed_from_reference", "surety_display",
            "created_at",
        ]

    def get_surety_display(self, obj) -> str | None:
        if not obj.surety_id:
            return None
        return getattr(obj.surety, "display_name", None) or str(obj.surety)

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


class GuaranteeReleaseRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    guarantee_reference = serializers.CharField(
        source="guarantee.reference", read_only=True
    )
    client_display = serializers.SerializerMethodField()

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
            "status",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_client_display(self, obj):
        client = obj.guarantee.client if obj.guarantee_id else None
        return getattr(client, "display_name", str(client)) if client else ""


class DationAssetSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(
        source="get_source_display", read_only=True
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
            "guarantee",
            "guarantee_reference",
            "guarantee_type_display",
            "description",
            "value",
            "created_at",
        ]
        read_only_fields = fields


class DationRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    client_display = serializers.SerializerMethodField()
    assets = DationAssetSerializer(many=True, read_only=True)
    assets_total_value = serializers.SerializerMethodField()
    covers_claim = serializers.SerializerMethodField()
    coverage_gap = serializers.SerializerMethodField()

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
            "assets_total_value",
            "covers_claim",
            "coverage_gap",
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
            "assets_total_value",
            "covers_claim",
            "coverage_gap",
        ]

    def get_client_display(self, obj):
        client = obj.client
        return getattr(client, "display_name", str(client)) if client else ""

    def get_assets_total_value(self, obj):
        return obj.assets_total_value()

    def get_covers_claim(self, obj):
        return obj.covers_claim()

    def get_coverage_gap(self, obj):
        claim = obj.cbs_total_outstanding
        if claim is None:
            return None
        return obj.assets_total_value() - claim
