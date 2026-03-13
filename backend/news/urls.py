from django.urls import path
from . import views

urlpatterns = [

    path('reporter-dashboard/', views.reporter_dashboard, name='reporter_dashboard'),

    path('create-article/', views.create_article, name='create_article'),

    path('subeditor-dashboard/', views.subeditor_dashboard, name='subeditor_dashboard'),

    path('edit-article/<int:article_id>/', views.edit_article, name='edit_article'),

    path('editor-dashboard/', views.editor_dashboard, name='editor_dashboard'),

    path('approve-article/<int:article_id>/', views.approve_article, name='approve_article'),

    path('pagination-dashboard/', views.pagination_dashboard, name='pagination_dashboard'),

    path('publish-article/<int:article_id>/', views.publish_article, name='publish_article'),

    path('send-back/<int:article_id>/', views.send_back_to_subeditor, name='send_back_to_subeditor'),

    path('restore-version/<int:version_id>/', views.restore_version, name='restore_version'),

    path('export-article/<int:article_id>/', views.export_article_xml, name='export_article_xml'),

    path('page-layout-planner/', views.page_layout_planner, name='page_layout_planner'),

    path('save-page-layout/', views.save_page_layout, name='save_page_layout'),

    path('export-page/<int:page_number>/', views.export_page_package, name='export_page_package'),

    path('export-quark/<int:page_number>/', views.export_quark_tagged_page, name='export_quark_tagged_page'),

    path('ai-improve-article/', views.ai_improve_article, name='ai_improve_article'),

    path('ai-generate-headline/', views.ai_generate_headline, name='ai_generate_headline'),

    path('ai-generate-article/', views.ai_generate_article, name='ai_generate_article'),

    path('archive-search/', views.archive_search, name='archive_search'),

    path('send-to-edition/<int:article_id>/', views.send_to_edition, name='send_to_edition'),

    path('edition-inbox/',views.edition_inbox,name='edition_inbox'),

    path('change-password/', views.change_password, name='change_password'),

    path('', views.login_redirect, name='login_redirect'),

#    path('ai-generate-from-urls/', views.ai_generate_article_from_urls, name='ai_generate_article_from_urls'),

]
