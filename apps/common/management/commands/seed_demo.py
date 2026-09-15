from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.forms_engine.models import DataSource,FormDefinition,FormVersion
from apps.knowledge.models import Article,KnowledgeCategory
from apps.organizations.models import Membership,Organization,Role,SupportGroup
from apps.public_site.models import NavigationItem,Service,SiteSettings,Statistic
from apps.quotations.models import Carrier,CarrierQuote,QuoteRequest
from apps.scheduler.models import ScheduledTask
from apps.scheduler.services import next_run
from apps.tickets.models import Category,Project,SLAPlan,Ticket
from apps.tickets.services import create_ticket
class Command(BaseCommand):
    help='Idempotently seed Alyusr demo/configuration data.'
    def add_arguments(self,parser):parser.add_argument('--password',default='AlyusrDemo!2026')
    def handle(self,*args,**options):
        User=get_user_model();password=options['password'];site,_=SiteSettings.objects.get_or_create(defaults={'site_name_en':'Alyusr Insurance Broker','site_name_ar':'اليسر لوساطة التأمين','hero_title_en':'Protection made clear. Service made simple.','hero_text_en':'Compare insurance options and manage service requests through one secure broker platform.'})
        for label,url,order in [('Home','/',10),('Knowledge Base','/portal/knowledge/',20),('Client Portal','/portal/',30)]:NavigationItem.objects.update_or_create(area='public',label_en=label,defaults={'url':url,'sort_order':order,'is_active':True})
        for title,icon,order in [('Motor Insurance','bi bi-car-front',10),('Health Insurance','bi bi-heart-pulse',20),('Travel Insurance','bi bi-airplane',30),('Business Insurance','bi bi-buildings',40)]:Service.objects.update_or_create(title_en=title,defaults={'icon':icon,'sort_order':order,'is_active':True})
        Statistic.objects.update_or_create(label_en='Digital service',defaults={'value':'24/7','sort_order':10})
        org,_=Organization.objects.update_or_create(code='alyusr-demo',defaults={'name':'Alyusr Demo Brokerage','is_active':True,'is_default_for_guests':True})
        users={}
        for username,email,role,staff in [('alyusr_admin','admin@alyusr.local',Role.ADMIN,True),('agent','agent@alyusr.local',Role.SUPPORT_AGENT,True),('requester','client@alyusr.local',Role.REQUESTER,False)]:
            user,created=User.objects.get_or_create(username=username,defaults={'email':email,'is_staff':staff});user.email=email;user.is_staff=staff
            if created or not user.has_usable_password():user.set_password(password)
            user.save();Membership.objects.update_or_create(organization=org,user=user,defaults={'role':role,'is_active':True});users[username]=user
        group,_=SupportGroup.objects.update_or_create(organization=org,code='service-desk',defaults={'name':'Service Desk','manager':users['alyusr_admin'],'is_active':True});group.members.add(users['alyusr_admin'],users['agent'])
        project,_=Project.objects.update_or_create(organization=org,code='client-service',defaults={'name':'Client Service','is_active':True});project.members.add(users['agent']);project.support_groups.add(group)
        sla,_=SLAPlan.objects.update_or_create(organization=org,name='Standard SLA',defaults={'response_minutes':60,'resolution_minutes':480,'warning_percent':80,'escalation_group':group,'auto_reassign_on_breach':True,'is_active':True})
        DataSource.objects.update_or_create(code='insurance-lines',defaults={'name':'Insurance Lines','kind':'static','config':{'values':[{'value':'motor','label':'Motor'},{'value':'health','label':'Health'},{'value':'travel','label':'Travel'}]},'is_active':True})
        form,_=FormDefinition.objects.update_or_create(code='general-service-request',defaults={'name':'General Service Request','module':'ticket','is_active':True});schema={'steps':[{'title':'Request','fields':[{'key':'line_of_business','label':'Line of business','type':'select','required':True,'datasource':'insurance-lines'},{'key':'policy_number','label':'Policy number','type':'text','sensitive':True}]},{'title':'Client details','fields':[{'key':'contact_phone','label':'Phone','type':'tel','sensitive':True}]},{'title':'Service details','fields':[{'key':'request_details','label':'Details','type':'textarea','required':True}]},{'title':'Review','fields':[{'key':'consent','label':'Confirm information','type':'checkbox','required':True}]}]};fv,_=FormVersion.objects.update_or_create(definition=form,version=1,defaults={'schema':schema,'is_published':True,'published_at':timezone.now(),'created_by':users['alyusr_admin']})
        category,_=Category.objects.update_or_create(organization=org,code='general-service',defaults={'name_en':'General Service Request','project':project,'default_group':group,'form_definition':form,'sla_plan':sla,'is_active':True})
        if not Ticket.objects.filter(organization=org,requester=users['requester']).exists():create_ticket(user=users['requester'],organization=org,category=category,subject='Policy endorsement request',description='Please update the insured vehicle details.',priority='normal',dynamic_data={'line_of_business':'motor','policy_number':'MTR-DEMO-1024','request_details':'Vehicle details changed.','consent':True},form_version=fv)
        carrier,_=Carrier.objects.update_or_create(code='demo-takaful',defaults={'name':'Demo Takaful','is_active':True});quote,_=QuoteRequest.objects.get_or_create(organization=org,requester=users['requester'],client_name='Demo Client',line_of_business='Motor',defaults={'status':'under_review','expires_at':timezone.now()+timezone.timedelta(days=14)});CarrierQuote.objects.update_or_create(quote_request=quote,carrier=carrier,defaults={'premium':125.5,'currency':'OMR','is_recommended':True})
        cat,_=KnowledgeCategory.objects.update_or_create(slug='motor',defaults={'name_en':'Motor Insurance'});Article.objects.update_or_create(slug='motor-claim-documents',defaults={'category':cat,'title_en':'Documents commonly needed for a motor claim','body_en':'Prepare the claim form, vehicle registration, driving licence, police report where applicable, and supporting photos.','status':'published','published_at':timezone.now(),'created_by':users['alyusr_admin']})
        task,_=ScheduledTask.objects.update_or_create(name='SLA compliance check',organization=org,defaults={'task_type':'sla','cron_expression':'*/5 * * * *','timezone':'Asia/Muscat','is_active':True,'created_by':users['alyusr_admin']});task.next_run_at=task.next_run_at or next_run(task);task.save()
        self.stdout.write(self.style.SUCCESS(f'Demo seeded. Users: admin@alyusr.local, agent@alyusr.local, client@alyusr.local | password: {password}'))
