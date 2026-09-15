from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("allauth.urls")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("portal/", include("apps.portal.urls")),
    path("portal/tickets/", include("apps.tickets.urls")),
    path("portal/quotations/", include("apps.quotations.urls")),
    path("portal/tasks/", include("apps.scheduler.urls")),
    path("portal/knowledge/", include("apps.knowledge.urls")),
    path("", include("apps.public_site.urls")),
    path("", include("cms.urls")),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
