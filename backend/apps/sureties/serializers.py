import json

from rest_framework import serializers

from apps.clients.serializers import PhonesInputField

from .models import Surety, SuretyDocument, SuretyEngagement, SuretyPhone


class SuretyEngagementSerializer(serializers.ModelSerializer):
    surety_display = serializers.CharField(
        source="surety.display_name", read_only=True
    )
    surety_activity = serializers.CharField(
        source="surety.activity", read_only=True
    )
    surety_type = serializers.CharField(
        source="surety.surety_type", read_only=True
    )
    surety_id_document_scan = serializers.FileField(
        source="surety.id_document_scan", read_only=True
    )
    surety_photo = serializers.ImageField(
        source="surety.photo", read_only=True
    )

    class Meta:
        model = SuretyEngagement
        fields = [
            "id", "surety", "surety_display", "surety_activity", "surety_type",
            "surety_id_document_scan", "surety_photo",
            "application", "amount", "signed_date", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SuretyPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuretyPhone
        fields = ["id", "number", "label"]


class SuretyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuretyDocument
        fields = ["id", "title", "file", "created_at"]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.common.storage_urls import file_download_url

        data["file"] = file_download_url(instance.file)
        return data


class SuretyListSerializer(serializers.ModelSerializer):
    """Liste allégée — sans engagements ni scans."""

    display_name = serializers.CharField(read_only=True)
    total_committed = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    available_ceiling = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )

    class Meta:
        model = Surety
        fields = [
            "id", "surety_type", "display_name", "agency", "phone", "city",
            "activity",
            "commitment_ceiling", "total_committed", "available_ceiling",
            "is_active", "created_at",
        ]
        read_only_fields = fields


class SuretySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    engagements = SuretyEngagementSerializer(many=True, read_only=True)
    phones = SuretyPhoneSerializer(many=True, read_only=True)
    documents = SuretyDocumentSerializer(many=True, read_only=True)
    additional_phones = PhonesInputField(write_only=True, required=False)
    total_committed = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    available_ceiling = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )

    class Meta:
        model = Surety
        fields = [
            "id", "surety_type", "display_name", "name", "agency",
            # Identité physique
            "first_name", "last_name", "birth_date", "birth_country",
            "activity", "estimated_income",
            # Pièce d'identité
            "id_document_type", "national_id", "id_document_issue_date",
            "id_document_expiry_date", "id_document_scan", "photo",
            # Entreprise
            "company_name", "legal_form", "ifu", "rccm",
            "ifu_scan", "rccm_scan", "city",
            # Gérant
            "manager_last_name", "manager_first_name", "manager_phone",
            "manager_email", "manager_address", "manager_id_document_type",
            "manager_id_document_number", "manager_id_document_issue_date",
            "manager_id_document_expiry_date", "manager_id_document_scan",
            "manager_position", "manager_birth_date", "manager_birth_country",
            "manager_birth_city",
            # Coordonnées
            "identifier", "phone", "email", "address",
            "phones", "additional_phones",
            # Documents libres
            "documents",
            # Engagement
            "commitment_ceiling", "total_committed", "available_ceiling",
            "is_active", "engagements", "created_at",
        ]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate(self, attrs):
        surety_type = attrs.get("surety_type") or getattr(
            self.instance, "surety_type", Surety.SuretyType.PHYSICAL
        )
        if surety_type == Surety.SuretyType.MORAL:
            company = attrs.get("company_name") or getattr(
                self.instance, "company_name", ""
            )
            name = attrs.get("name") or getattr(self.instance, "name", "")
            if not (company or name):
                raise serializers.ValidationError(
                    {"company_name": "La raison sociale de la caution est obligatoire."}
                )
        else:
            last_name = attrs.get("last_name") or getattr(
                self.instance, "last_name", ""
            )
            name = attrs.get("name") or getattr(self.instance, "name", "")
            if not (last_name or name):
                raise serializers.ValidationError(
                    {"last_name": "Le nom de la caution est obligatoire."}
                )
        return attrs

    def _sync_phones(self, surety, phones):
        for entry in phones:
            SuretyPhone.objects.create(
                surety=surety, number=entry["number"], label=entry.get("label", "")
            )

    def _save_documents(self, surety):
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
            surety.documents.filter(id__in=delete_ids).delete()

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
            SuretyDocument.objects.create(
                surety=surety,
                tenant_id=surety.tenant_id,
                title=title[:200],
                file=uploaded,
            )

    def create(self, validated_data):
        phones = validated_data.pop("additional_phones", None)
        surety = super().create(validated_data)
        if phones:
            self._sync_phones(surety, phones)
        self._save_documents(surety)
        return surety

    def update(self, instance, validated_data):
        phones = validated_data.pop("additional_phones", None)
        surety = super().update(instance, validated_data)
        if phones is not None:
            instance.phones.all().delete()
            self._sync_phones(surety, phones)
        self._save_documents(surety)
        return surety
