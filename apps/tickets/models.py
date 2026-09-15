import secrets
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import Organization, SupportGroup


def ticket_reference():
    return f"TKT-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def share_token():
    return secrets.token_urlsafe(32)


def validate_attachment(file):
    allowed = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"}
    ext = Path(file.name).suffix.lower()
    if ext not in allowed:
        raise ValidationError(f"File type {ext or '(none)'} is not allowed.")
    if file.size > getattr(settings, "MAX_UPLOAD_MB", 20) * 1024 * 1024:
        raise ValidationError("Attachment exceeds configured limit.")


class Project(UUIDTimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=140)
    code = models.SlugField(max_length=60)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="alyusr_projects")
    support_groups = models.ManyToManyField(SupportGroup, blank=True, related_name="projects")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="uniq_org_project_code")]

    def __str__(self):
        return self.name


class SLAPlan(UUIDTimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sla_plans")
    name = models.CharField(max_length=120)
    response_minutes = models.PositiveIntegerField(default=60)
    resolution_minutes = models.PositiveIntegerField(default=480)
    warning_percent = models.PositiveSmallIntegerField(default=80)
    escalation_group = models.ForeignKey(SupportGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="sla_escalations")
    escalation_levels = models.JSONField(default=list, blank=True, help_text="Ordered escalation thresholds and target user/group definitions")
    escalate_to_reporting_manager = models.BooleanField(default=True)
    auto_reassign_on_breach = models.BooleanField(default=False)
    business_hours_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(UUIDTimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="ticket_categories")
    name_en = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True)
    code = models.SlugField(max_length=80)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="categories")
    default_group = models.ForeignKey(SupportGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="default_categories")
    form_definition = models.ForeignKey("forms_engine.FormDefinition", null=True, blank=True, on_delete=models.SET_NULL, related_name="ticket_categories")
    sla_plan = models.ForeignKey(SLAPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name="categories")
    required_documents = models.JSONField(default=list, blank=True)
    approval_levels = models.JSONField(default=list, blank=True)
    send_initial_email = models.BooleanField(default=True)
    send_update_email = models.BooleanField(default=True)
    auto_close_days = models.PositiveSmallIntegerField(null=True, blank=True)
    reopen_window_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="uniq_org_ticket_category_code")]

    def __str__(self):
        return self.name_en


class TicketQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self
        orgs = user.organization_memberships.filter(is_active=True).values_list("organization_id", flat=True)
        return self.filter(organization_id__in=orgs).filter(
            Q(requester=user) | Q(assigned_users=user) | Q(assigned_groups__members=user) | Q(project__members=user)
        ).distinct()


class Ticket(UUIDTimeStampedModel):
    class WorkType(models.TextChoices):
        SERVICE = "service", "Service Ticket"
        QUOTATION = "quotation", "Quotation"
        TASK = "task", "Task Generated"
        RENEWAL = "renewal", "Renewal"
        CLAIM = "claim", "Claim Service"

    class Origin(models.TextChoices):
        MANUAL = "manual", "Manual"
        TASK = "task", "Scheduled Task"
        RENEWAL = "renewal", "Renewal Automation"
        QUOTATION = "quotation", "Quotation"
        CLAIM = "claim", "Claim"
        API = "api", "API"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        PENDING = "pending", "Pending"
        APPROVAL = "approval", "Awaiting approval"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    reference = models.CharField(max_length=40, unique=True, default=ticket_reference, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="tickets")
    work_type = models.CharField(max_length=16, choices=WorkType.choices, default=WorkType.SERVICE, db_index=True)
    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.MANUAL, db_index=True)
    source_reference = models.CharField(max_length=120, blank=True, db_index=True)
    parent_ticket = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="child_tickets")
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    client_product = models.ForeignKey("clients.ClientProduct", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="tickets")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_tickets")
    subject = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="assigned_tickets")
    assigned_groups = models.ManyToManyField(SupportGroup, blank=True, related_name="assigned_tickets")
    form_version = models.ForeignKey("forms_engine.FormVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="tickets")
    dynamic_data = models.JSONField(default=dict, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    renewal_due_on = models.DateField(null=True, blank=True, db_index=True)
    sla_warning_sent_at = models.DateTimeField(null=True, blank=True)
    sla_breached_at = models.DateTimeField(null=True, blank=True)

    objects = TicketQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["organization", "work_type", "status"]), models.Index(fields=["client", "client_product"])]

    def __str__(self):
        return f"{self.reference} · {self.subject}"

    @property
    def is_open(self):
        return self.status not in {self.Status.CLOSED, self.Status.CANCELLED}

    @property
    def sla_plan(self):
        return self.category.sla_plan

    @property
    def sla_percent(self):
        if not self.due_at:
            return None
        total = max((self.due_at - self.created_at).total_seconds(), 1)
        elapsed = max((timezone.now() - self.created_at).total_seconds(), 0)
        return min(round(elapsed / total * 100, 1), 999.9)


class TicketComment(UUIDTimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="ticket_comments")
    body = models.TextField()
    body_html = models.TextField(blank=True)
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ("created_at",)

    def save(self, *args, **kwargs):
        import bleach
        allowed = set(bleach.sanitizer.ALLOWED_TAGS).union({"p", "br", "div", "span", "ul", "ol", "li", "strong", "em", "blockquote"})
        self.body_html = bleach.clean(self.body, tags=allowed, attributes={"a": ["href", "title", "target"]}, strip=True)
        super().save(*args, **kwargs)


class TicketAttachment(UUIDTimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    comment = models.ForeignKey(TicketComment, null=True, blank=True, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="ticket_attachments")
    file = models.FileField(upload_to="tickets/%Y/%m/", validators=[validate_attachment])
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    is_sensitive = models.BooleanField(default=False)


class TicketActivity(UUIDTimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ticket_activities")
    action = models.CharField(max_length=80)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)


class TicketApproval(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="approvals")
    level = models.PositiveSmallIntegerField(default=1)
    approver_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ticket_approvals")
    approver_group = models.ForeignKey(SupportGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="ticket_approvals")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)


class TicketSLAEvent(UUIDTimeStampedModel):
    class Event(models.TextChoices):
        WARNING = "warning", "Warning"
        BREACH = "breach", "Breach"
        ESCALATION = "escalation", "Escalation"
        RECOVERED = "recovered", "Recovered"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="sla_events")
    event = models.CharField(max_length=20, choices=Event.choices)
    level = models.PositiveSmallIntegerField(null=True, blank=True)
    threshold_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)


class TicketShare(UUIDTimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="shares")
    token = models.CharField(max_length=64, unique=True, editable=False, default=share_token)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="ticket_shares")
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    can_download = models.BooleanField(default=True)

    def is_valid(self):
        return not self.revoked_at and timezone.now() < self.expires_at
