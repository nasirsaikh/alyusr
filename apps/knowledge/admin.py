from django.contrib import admin
from .models import Article,ArticleVersion,KnowledgeCategory
admin.site.register(KnowledgeCategory);admin.site.register(Article);admin.site.register(ArticleVersion)
