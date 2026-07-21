from django.urls import path
from .views import ARFilterListView, ARFilterDetailView, ARFilterManifestView, ARFilterBulkCreateView

urlpatterns = [
    path('', ARFilterListView.as_view(), name='ar-filter-list'),
    path('<uuid:pk>/', ARFilterDetailView.as_view(), name='ar-filter-detail'),
    path('manifest/', ARFilterManifestView.as_view(), name='ar-filter-manifest'),
    path('bulk-create/', ARFilterBulkCreateView.as_view(), name='ar-filter-bulk-create'),
]
