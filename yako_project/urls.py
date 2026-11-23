from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from app_qvac_financial.server.api.public.views import landing

urlpatterns = [
    path('', landing, name='home'),
    path('qvac-financial/', RedirectView.as_view(pattern_name='home', query_string=True)),
    path('admin/', admin.site.urls),
    path('qvac-financial/', include('app_qvac_financial.urls')),
]