from django.conf import settings
from django.db import models
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import Organization
from apps.tickets.models import validate_attachment


class Client(UUIDTimeStampedModel):
    class ClientType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        CORPORATE = "corporate", "Corporate"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="clients")
    portal_user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="insurance_client")
    client_number = models.CharField(max_length=80)
    client_type = models.CharField(max_length=16, choices=ClientType.choices, default=ClientType.INDIVIDUAL)
    name = models.CharField(max_length=180)
    name_ar = models.CharField(max_length=180, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    identity_reference = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    account_manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_insurance_clients")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "client_number"], name="uniq_org_client_number")]
        ordering = ("name",)

    def __str__(self):
        return f"{self.client_number} · {self.name}"


class InsuranceProduct(UUIDTimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="insurance_products")
    code = models.SlugField(max_length=60)
    name_en = models.CharField(max_length=140)
    name_ar = models.CharField(max_length=140, blank=True)
    category = models.CharField(max_length=80, blank=True)
    default_renewal_lead_days = models.PositiveSmallIntegerField(default=30)
    description_en = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="uniq_org_insurance_product")]
        ordering = ("name_en",)

    def __str__(self):
        return self.name_en


class ClientProduct(UUIDTimeStampedModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="products")
    product = models.ForeignKey(InsuranceProduct, on_delete=models.PROTECT, related_name="client_products")
    reference_name = models.CharField(max_length=140, blank=True, help_text="Optional scheme, fleet, branch or risk name")
    external_reference = models.CharField(max_length=120, blank=True)
    renewal_lead_days = models.PositiveSmallIntegerField(default=30)
    next_renewal_date = models.DateField(null=True, blank=True, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_client_products")
    current_policy = models.ForeignKey("Policy", null=True, blank=True, on_delete=models.SET_NULL, related_name="current_for_client_products")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "product", "reference_name"], name="uniq_client_product_reference")]
        ordering = ("client__name", "product__name_en", "reference_name")

    def __str__(self):
        suffix = f" / {self.reference_name}" if self.reference_name else ""
        return f"{self.client.name} · {self.product.name_en}{suffix}"

    def save(self, *args, **kwargs):
        if not self.renewal_lead_days and self.product_id:
            self.renewal_lead_days = self.product.default_renewal_lead_days
        super().save(*args, **kwargs)


class Policy(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="policies")
    client_product = models.ForeignKey(ClientProduct, null=True, blank=True, on_delete=models.SET_NULL, related_name="policies")
    product = models.ForeignKey(InsuranceProduct, null=True, blank=True, on_delete=models.SET_NULL, related_name="policies")
    carrier = models.ForeignKey("quotations.Carrier", null=True, blank=True, on_delete=models.SET_NULL, related_name="policies")
    source_quote_request = models.ForeignKey("quotations.QuoteRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="bound_policies")
    policy_number = models.CharField(max_length=120)
    line_of_business = models.CharField(max_length=80, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(db_index=True)
    premium = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    currency = models.CharField(max_length=3, default="OMR")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    renewal_reminder_days = models.PositiveSmallIntegerField(default=30)
    autopay_enabled = models.BooleanField(default=False)
    autopay_external_reference = models.CharField(max_length=160, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "policy_number"], name="uniq_client_policy_number")]
        ordering = ("-end_date",)

    def __str__(self):
        return self.policy_number


class Claim(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        FILED = "filed", "Filed"
        REVIEW = "review", "Under Review"
        DOCUMENTS = "documents", "Documents Required"
        APPROVED = "approved", "Approved"
        SETTLED = "settled", "Settled"
        REJECTED = "rejected", "Rejected"
        CLOSED = "closed", "Closed"

    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="claims")
    claim_number = models.CharField(max_length=120, blank=True)
    loss_date = models.DateField()
    reported_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FILED, db_index=True)
    settlement_amount = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    service_ticket = models.OneToOneField("tickets.Ticket", null=True, blank=True, on_delete=models.SET_NULL, related_name="claim")


class ClientDocument(UUIDTimeStampedModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    client_product = models.ForeignKey(ClientProduct, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    policy = models.ForeignKey(Policy, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    claim = models.ForeignKey(Claim, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    category = models.CharField(max_length=40, default="other")
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to="client_vault/%Y/%m/", validators=[validate_attachment])
    expires_on = models.DateField(null=True, blank=True, db_index=True)
    client_visible = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="client_documents")


class BillingTransaction(UUIDTimeStampedModel):
    class TxType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"
        ADJUSTMENT = "adjustment", "Adjustment"

    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="billing_transactions")
    tx_type = models.CharField(max_length=16, choices=TxType.choices)
    reference = models.CharField(max_length=120)
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=3)
    currency = models.CharField(max_length=3, default="OMR")
    payment_method = models.CharField(max_length=40, blank=True)
    external_payment_reference = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
