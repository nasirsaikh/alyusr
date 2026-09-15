from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.clients.models import Client, ClientProduct, InsuranceProduct, Policy
from apps.forms_engine.models import DataSource, FormDefinition, FormVersion
from apps.knowledge.models import Article, KnowledgeCategory
from apps.organizations.models import Membership, Organization, Role, SupportGroup
from apps.public_site.models import CarrierTrustBadge, ClientLogo, FAQ, NavigationItem, PageSection, Service, SiteSettings, Statistic, Testimonial
from apps.quotations.models import Carrier, CarrierQuote, QuoteParticipant, QuoteRequest
from apps.scheduler.models import ScheduledTask
from apps.scheduler.services import next_run
from apps.tickets.models import Category, Project, SLAPlan, Ticket
from apps.tickets.services import create_ticket


class Command(BaseCommand):
    help = "Idempotently seed Alyusr demo/configuration data."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        demo_password = options["password"]

        site = SiteSettings.objects.first() or SiteSettings()
        site.site_name_en = "Alyusr Insurance Broker"
        site.site_name_ar = "اليسر لوساطة التأمين"
        site.short_name = "Alyusr"
        site.tagline_en = "Insurance brokerage, client service and renewals on one governed platform."
        site.tagline_ar = "وساطة التأمين وخدمة العملاء والتجديدات في منصة موحدة."
        site.hero_eyebrow_en = "Enterprise insurance service platform"
        site.hero_eyebrow_ar = "منصة خدمات تأمين مؤسسية"
        site.hero_title_en = "Quotation, service and renewal operations — connected from the first request."
        site.hero_title_ar = "عروض الأسعار والخدمة والتجديد — مترابطة من أول طلب."
        site.hero_text_en = "Alyusr brings quotations, recurring tasks and service tickets into one auditable workflow with dynamic forms, SLA automation, approvals, documents and client visibility."
        site.hero_text_ar = "تجمع اليسر عروض الأسعار والمهام المتكررة وتذاكر الخدمة في سير عمل واحد مع النماذج الديناميكية وSLA والموافقات والمستندات ورؤية العميل."
        site.primary_cta_label_en = "Request a Quote"
        site.primary_cta_label_ar = "اطلب عرض سعر"
        site.primary_cta_url = "/portal/quotations/"
        site.secondary_cta_label_en = "Open Client Portal"
        site.secondary_cta_label_ar = "افتح بوابة العملاء"
        site.secondary_cta_url = "/portal/"
        site.about_title_en = "Broker service designed around the complete client lifecycle."
        site.about_title_ar = "خدمة وساطة مصممة حول دورة حياة العميل بالكامل."
        site.about_text_en = "Alyusr connects client products, insurers, quotations, policies, renewals and service requests so teams work from the same operational record and clients receive consistent service."
        site.about_text_ar = "تربط اليسر منتجات العملاء وشركات التأمين وعروض الأسعار والوثائق والتجديدات وطلبات الخدمة بحيث تعمل الفرق من سجل تشغيلي موحد."
        site.trust_title_en = "Governed by role, organization, SLA and audit history"
        site.trust_title_ar = "حوكمة حسب الدور والمؤسسة وSLA وسجل التدقيق"
        site.trust_text_en = "Sensitive fields can be masked, access is enforced server-side, approvals are traceable and each change remains part of the work history."
        site.trust_text_ar = "يمكن إخفاء الحقول الحساسة ويتم فرض الوصول على الخادم وتبقى الموافقات والتغييرات قابلة للتتبع."
        site.footer_text_en = "A bilingual enterprise platform for insurance quotations, renewals, recurring work and client service tickets."
        site.footer_text_ar = "منصة مؤسسية ثنائية اللغة لعروض التأمين والتجديدات والمهام المتكررة وتذاكر خدمة العملاء."
        site.save()

        navigation = [
            ("Home", "الرئيسية", "/", 10),
            ("Platform", "المنصة", "/#platform", 20),
            ("Services", "الخدمات", "/#services", 30),
            ("About", "من نحن", "/#about", 40),
            ("Contact", "اتصل بنا", "/#contact", 50),
        ]
        for label, label_ar, url, order in navigation:
            NavigationItem.objects.update_or_create(area=NavigationItem.Area.PUBLIC, label_en=label, defaults={"label_ar": label_ar, "url": url, "sort_order": order, "is_active": True})
        for label, label_ar, url, order in navigation[1:]:
            NavigationItem.objects.update_or_create(area=NavigationItem.Area.FOOTER, label_en=label, defaults={"label_ar": label_ar, "url": url, "sort_order": order, "is_active": True})

        services = [
            ("Motor Insurance", "تأمين المركبات", "Motor placement, fleet renewals, endorsements and claims servicing.", "bi bi-car-front", 10),
            ("Medical Insurance", "التأمين الصحي", "Employee medical programmes, market comparison and annual renewal management.", "bi bi-heart-pulse", 20),
            ("Property Insurance", "تأمين الممتلكات", "Property and business interruption placement with structured risk documentation.", "bi bi-buildings", 30),
            ("Marine Insurance", "التأمين البحري", "Cargo, hull and marine-related quotation and servicing workflows.", "bi bi-water", 40),
            ("Travel Insurance", "تأمين السفر", "Individual and corporate travel coverage with digital servicing.", "bi bi-airplane", 50),
            ("Liability & Business", "المسؤولية والأعمال", "Liability, engineering and specialist business insurance programmes.", "bi bi-briefcase", 60),
        ]
        for title, title_ar, description, icon, order in services:
            Service.objects.update_or_create(title_en=title, defaults={"title_ar": title_ar, "description_en": description, "icon": icon, "sort_order": order, "is_active": True})

        stats = [
            ("Digital client service", "خدمة عملاء رقمية", "24/7", "bi bi-clock", 10),
            ("Operational applications", "تطبيقات تشغيلية", "3", "bi bi-grid", 20),
            ("Ticket creation steps", "خطوات إنشاء التذكرة", "4", "bi bi-ui-checks-grid", 30),
            ("Audit trail", "سجل التدقيق", "360°", "bi bi-clock-history", 40),
        ]
        for label, label_ar, value, icon, order in stats:
            Statistic.objects.update_or_create(label_en=label, defaults={"label_ar": label_ar, "value": value, "icon": icon, "sort_order": order, "is_active": True})

        sections = [
            ("Dynamic JSON Forms", "نماذج JSON ديناميكية", "Four-step ticket forms with conditional rules, role visibility, server validation and allowlisted lookup sources.", "bi bi-ui-checks-grid", "platform", 10),
            ("Executable SLA Automation", "أتمتة SLA قابلة للتنفيذ", "Warning thresholds, breach events, support-group escalation and reporting-manager escalation are part of the workflow.", "bi bi-stopwatch", "process", 20),
            ("Knowledge & AI Assistance", "المعرفة والمساعدة الذكية", "A bilingual knowledge base supports consistent answers and provides the foundation for suggested articles and next-best actions.", "bi bi-journal-richtext", "knowledge", 30),
            ("Secure Client Collaboration", "تعاون آمن مع العملاء", "Controlled sharing, document visibility, audit history and server-side organization isolation protect client servicing.", "bi bi-shield-lock", "security", 40),
            ("Approvals & Full Audit", "الموافقات والتدقيق الكامل", "Multi-level approvals, assignment history, takeover actions and activity logs make accountability visible.", "bi bi-check2-square", "process", 50),
            ("Notifications & Follow-up", "الإشعارات والمتابعة", "Assignments, SLA warnings, approvals, ticket updates and renewal actions can generate in-app and email notifications.", "bi bi-bell", "platform", 60),
        ]
        for title, title_ar, body, icon, section_type, order in sections:
            PageSection.objects.update_or_create(title_en=title, defaults={"title_ar": title_ar, "body_en": body, "icon": icon, "section_type": section_type, "sort_order": order, "is_active": True})

        faqs = [
            ("Can one client have multiple insurance products?", "Yes. Each client product has its own policies, renewal date and quotation workflow."),
            ("How are insurer participants tracked?", "Every invited insurer has a participation record. Actual quotations are stored separately for comparison and award."),
            ("Can renewals create quotation requests automatically?", "Yes. A renewal task can be linked to a client product, ticket category and selected insurers and generate the quotation ticket automatically."),
            ("Is ticket access controlled on the server?", "Yes. Visibility is restricted by organization membership plus requester, assignee, project and support-group scope."),
        ]
        for order, (question, answer) in enumerate(faqs, start=1):
            FAQ.objects.update_or_create(question_en=question, defaults={"answer_en": answer, "sort_order": order * 10, "is_active": True})

        Testimonial.objects.update_or_create(client_name="Demo Corporate Client", defaults={"client_title": "Insurance programme administrator", "quote_en": "The unified ticket and quotation trail makes renewals and service follow-up much easier to monitor.", "sort_order": 10, "is_active": True})
        ClientLogo.objects.update_or_create(name="Demo Corporate Client", defaults={"sort_order": 10, "is_active": True})
        CarrierTrustBadge.objects.update_or_create(name="Demo Takaful", defaults={"sort_order": 10, "is_active": True})
        CarrierTrustBadge.objects.update_or_create(name="Demo Insurance Co.", defaults={"sort_order": 20, "is_active": True})

        org, _ = Organization.objects.update_or_create(code="alyusr-demo", defaults={"name": "Alyusr Demo Brokerage", "is_active": True, "is_default_for_guests": True})
        users = {}
        for username, email, role, staff in [
            ("alyusr_admin", "admin@alyusr.local", Role.ADMIN, True),
            ("agent", "agent@alyusr.local", Role.SUPPORT_AGENT, True),
            ("requester", "client@alyusr.local", Role.REQUESTER, False),
        ]:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email, "is_staff": staff})
            user.email = email
            user.is_staff = staff
            if created or not user.has_usable_password():
                user.set_password(demo_password)
            user.save()
            Membership.objects.update_or_create(organization=org, user=user, defaults={"role": role, "is_active": True})
            users[username] = user

        group, _ = SupportGroup.objects.update_or_create(organization=org, code="service-desk", defaults={"name": "Client Service Desk", "manager": users["alyusr_admin"], "is_active": True})
        group.members.add(users["alyusr_admin"], users["agent"])
        project, _ = Project.objects.update_or_create(organization=org, code="client-service", defaults={"name": "Client Service & Placement", "is_active": True})
        project.members.add(users["agent"])
        project.support_groups.add(group)
        sla, _ = SLAPlan.objects.update_or_create(organization=org, name="Standard SLA", defaults={"response_minutes": 60, "resolution_minutes": 480, "warning_percent": 80, "escalation_group": group, "auto_reassign_on_breach": True, "escalate_to_reporting_manager": True, "is_active": True})

        DataSource.objects.update_or_create(code="insurance-lines", defaults={"name": "Insurance Lines", "kind": "static", "config": {"values": [{"value": "motor", "label": "Motor"}, {"value": "medical", "label": "Medical"}, {"value": "property", "label": "Property"}, {"value": "travel", "label": "Travel"}]}, "is_active": True})
        form, _ = FormDefinition.objects.update_or_create(code="general-service-request", defaults={"name": "General Service Request", "module": "ticket", "is_active": True})
        schema = {"steps": [{"title": "Request", "fields": [{"key": "line_of_business", "label": "Line of business", "type": "select", "required": True, "datasource": "insurance-lines"}, {"key": "policy_number", "label": "Policy number", "type": "text", "sensitive": True}]}, {"title": "Client details", "fields": [{"key": "contact_phone", "label": "Phone", "type": "tel", "sensitive": True}]}, {"title": "Service details", "fields": [{"key": "request_details", "label": "Details", "type": "textarea", "required": True}]}, {"title": "Review", "fields": [{"key": "consent", "label": "Confirm information", "type": "checkbox", "required": True}]}]}
        fv, _ = FormVersion.objects.update_or_create(definition=form, version=1, defaults={"schema": schema, "is_published": True, "published_at": timezone.now(), "created_by": users["alyusr_admin"]})
        service_category, _ = Category.objects.update_or_create(organization=org, code="general-service", defaults={"name_en": "General Service Request", "project": project, "default_group": group, "form_definition": form, "sla_plan": sla, "is_active": True})
        quote_category, _ = Category.objects.update_or_create(organization=org, code="quotation-renewal", defaults={"name_en": "Quotation & Renewal", "project": project, "default_group": group, "sla_plan": sla, "required_documents": ["Existing policy", "Updated client/risk information"], "is_active": True})

        client, _ = Client.objects.update_or_create(organization=org, client_number="DEMO-001", defaults={"portal_user": users["requester"], "client_type": Client.ClientType.CORPORATE, "name": "Demo Corporate Client", "email": users["requester"].email, "account_manager": users["agent"], "is_active": True})
        motor, _ = InsuranceProduct.objects.update_or_create(organization=org, code="motor", defaults={"name_en": "Motor Insurance", "name_ar": "تأمين المركبات", "category": "General", "default_renewal_lead_days": 30, "is_active": True})
        medical, _ = InsuranceProduct.objects.update_or_create(organization=org, code="medical", defaults={"name_en": "Medical Insurance", "name_ar": "التأمين الصحي", "category": "Health", "default_renewal_lead_days": 45, "is_active": True})
        motor_product, _ = ClientProduct.objects.update_or_create(client=client, product=motor, reference_name="Corporate Fleet", defaults={"renewal_lead_days": 30, "next_renewal_date": timezone.localdate() + timezone.timedelta(days=25), "assigned_to": users["agent"], "is_active": True})
        ClientProduct.objects.update_or_create(client=client, product=medical, reference_name="Employee Medical Scheme", defaults={"renewal_lead_days": 45, "next_renewal_date": timezone.localdate() + timezone.timedelta(days=120), "assigned_to": users["agent"], "is_active": True})

        carrier_a, _ = Carrier.objects.update_or_create(code="demo-takaful", defaults={"name": "Demo Takaful", "is_active": True})
        carrier_b, _ = Carrier.objects.update_or_create(code="demo-insurance", defaults={"name": "Demo Insurance Co.", "is_active": True})
        policy, _ = Policy.objects.update_or_create(client=client, policy_number="MTR-DEMO-2026", defaults={"client_product": motor_product, "product": motor, "carrier": carrier_a, "line_of_business": "Motor", "start_date": timezone.localdate() - timezone.timedelta(days=340), "end_date": motor_product.next_renewal_date, "premium": 2450, "currency": "OMR", "status": Policy.Status.ACTIVE, "renewal_reminder_days": 30})
        if motor_product.current_policy_id != policy.pk:
            motor_product.current_policy = policy
            motor_product.save(update_fields=["current_policy", "updated_at"])

        if not Ticket.objects.filter(organization=org, requester=users["requester"], work_type=Ticket.WorkType.SERVICE).exists():
            create_ticket(user=users["requester"], organization=org, category=service_category, subject="Policy endorsement request", description="Please update the insured vehicle details.", priority=Ticket.Priority.NORMAL, dynamic_data={"line_of_business": "motor", "policy_number": "MTR-DEMO-2026", "request_details": "Vehicle details changed.", "consent": True}, form_version=fv, client=client, client_product=motor_product)

        quote_ticket = Ticket.objects.filter(organization=org, client_product=motor_product, source_reference="DEMO-RENEWAL-MOTOR").first()
        if not quote_ticket:
            quote_ticket = create_ticket(user=users["agent"], organization=org, category=quote_category, subject="Motor renewal quotation - Demo Corporate Client", description="Renewal marketing and quotation comparison for the corporate fleet.", priority=Ticket.Priority.HIGH, work_type=Ticket.WorkType.RENEWAL, origin=Ticket.Origin.RENEWAL, client=client, client_product=motor_product, source_reference="DEMO-RENEWAL-MOTOR", renewal_due_on=motor_product.next_renewal_date)
        quote, _ = QuoteRequest.objects.update_or_create(ticket=quote_ticket, defaults={"organization": org, "requester": users["agent"], "client": client, "client_product": motor_product, "renewal_of_policy": policy, "request_type": QuoteRequest.RequestType.RENEWAL, "client_name": client.name, "client_email": client.email, "line_of_business": motor.name_en, "status": QuoteRequest.Status.AWARDED, "market_due_at": timezone.now() + timezone.timedelta(days=7)})
        part_a, _ = QuoteParticipant.objects.update_or_create(quote_request=quote, carrier=carrier_a, defaults={"status": QuoteParticipant.Status.QUOTED, "responded_at": timezone.now(), "assigned_to": users["agent"]})
        part_b, _ = QuoteParticipant.objects.update_or_create(quote_request=quote, carrier=carrier_b, defaults={"status": QuoteParticipant.Status.QUOTED, "responded_at": timezone.now(), "assigned_to": users["agent"]})
        winning_quote, _ = CarrierQuote.objects.update_or_create(quote_request=quote, carrier=carrier_a, defaults={"participant": part_a, "quote_number": "DT-REN-001", "premium": 2380, "currency": "OMR", "deductible": 100, "sum_insured": 150000, "valid_until": timezone.localdate() + timezone.timedelta(days=20), "score": 91, "is_recommended": True, "is_winner": True})
        CarrierQuote.objects.update_or_create(quote_request=quote, carrier=carrier_b, defaults={"participant": part_b, "quote_number": "DI-REN-002", "premium": 2525, "currency": "OMR", "deductible": 75, "sum_insured": 150000, "valid_until": timezone.localdate() + timezone.timedelta(days=20), "score": 86, "is_recommended": False, "is_winner": False})
        if quote.selected_quote_id != winning_quote.pk:
            quote.selected_quote = winning_quote
            quote.awarded_at = quote.awarded_at or timezone.now()
            quote.save(update_fields=["selected_quote", "awarded_at", "updated_at"])

        kb_category, _ = KnowledgeCategory.objects.update_or_create(slug="motor", defaults={"name_en": "Motor Insurance"})
        Article.objects.update_or_create(slug="motor-claim-documents", defaults={"category": kb_category, "title_en": "Documents commonly needed for a motor claim", "body_en": "Prepare the claim form, vehicle registration, driving licence, police report where applicable, and supporting photos.", "status": "published", "published_at": timezone.now(), "created_by": users["alyusr_admin"]})

        sla_task, _ = ScheduledTask.objects.update_or_create(name="SLA compliance check", organization=org, defaults={"task_type": ScheduledTask.TaskType.SLA, "cron_expression": "*/5 * * * *", "timezone": "Asia/Muscat", "is_active": True, "created_by": users["alyusr_admin"]})
        sla_task.next_run_at = sla_task.next_run_at or next_run(sla_task)
        sla_task.save()
        renewal_task, _ = ScheduledTask.objects.update_or_create(name="Demo motor renewal automation", organization=org, defaults={"task_type": ScheduledTask.TaskType.RENEWAL, "cron_expression": "0 8 * * *", "timezone": "Asia/Muscat", "ticket_category": quote_category, "client": client, "client_product": motor_product, "payload": {"subject": "Automated motor renewal quotation", "priority": "high"}, "is_active": True, "created_by": users["alyusr_admin"]})
        renewal_task.quote_carriers.set([carrier_a, carrier_b])
        renewal_task.next_run_at = renewal_task.next_run_at or next_run(renewal_task)
        renewal_task.save()

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully. Use the password supplied to --password for the demo users."))
