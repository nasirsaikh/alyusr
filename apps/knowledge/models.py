from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import Organization
class KnowledgeCategory(UUIDTimeStampedModel):
    name_en=models.CharField(max_length=120); name_ar=models.CharField(max_length=120,blank=True); slug=models.SlugField(max_length=100,unique=True); sort_order=models.PositiveSmallIntegerField(default=10); is_active=models.BooleanField(default=True)
    class Meta: ordering=('sort_order','name_en')
    def __str__(self):return self.name_en
class Article(UUIDTimeStampedModel):
    class Status(models.TextChoices): DRAFT='draft','Draft'; REVIEW='review','Under Review'; PUBLISHED='published','Published'; ARCHIVED='archived','Archived'
    organization=models.ForeignKey(Organization,null=True,blank=True,on_delete=models.CASCADE,related_name='knowledge_articles'); category=models.ForeignKey(KnowledgeCategory,on_delete=models.PROTECT,related_name='articles'); slug=models.SlugField(max_length=160,unique=True); title_en=models.CharField(max_length=220); title_ar=models.CharField(max_length=220,blank=True); summary_en=models.TextField(blank=True); summary_ar=models.TextField(blank=True); body_en=models.TextField(); body_ar=models.TextField(blank=True); tags=models.JSONField(default=list,blank=True); status=models.CharField(max_length=16,choices=Status.choices,default=Status.DRAFT,db_index=True); published_at=models.DateTimeField(null=True,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='created_kb_articles'); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='approved_kb_articles')
    def publish(self,user=None):self.status=self.Status.PUBLISHED;self.published_at=timezone.now();self.approved_by=user;self.save()
    def __str__(self):return self.title_en
class ArticleVersion(UUIDTimeStampedModel):
    article=models.ForeignKey(Article,on_delete=models.CASCADE,related_name='versions'); version=models.PositiveIntegerField(); title_en=models.CharField(max_length=220); title_ar=models.CharField(max_length=220,blank=True); body_en=models.TextField(); body_ar=models.TextField(blank=True); change_note=models.CharField(max_length=255,blank=True); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='kb_versions')
    class Meta: constraints=[models.UniqueConstraint(fields=['article','version'],name='uniq_article_version')]
