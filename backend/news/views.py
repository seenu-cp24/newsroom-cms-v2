import os
import zipfile
import xml.etree.ElementTree as ET
from .utils import get_editorial_date

from django.shortcuts import render, redirect
from django.http import FileResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import (
    Article,
    ArticleImage,
    ArticleVersion,
    Category,
    ArticleActivity,
    PageLayout,
    Edition
)

from .ai_services import improve_article, generate_headline, generate_article_from_notes


# -----------------------------------
# REPORTER DASHBOARD
# -----------------------------------

@login_required
def reporter_dashboard(request):

    edition = request.user.userprofile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        reporter=request.user,
        edition=edition,
        edition_date=today
    )

    return render(request,'news/reporter_dashboard.html',{
        'articles':articles
    })


# -----------------------------------
# CREATE ARTICLE
# -----------------------------------

@login_required
def create_article(request):

    edition = request.user.userprofile.edition

    categories = Category.objects.filter(edition=edition)

    if request.method == "POST":

        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category")

        category = Category.objects.filter(id=category_id).first()

        if not category:
            return redirect('/create-article/')

        role = request.user.userprofile.role

        if role == "reporter":
            status = "submitted"

        elif role == "subeditor":
            status = "subeditor_review"

        elif role == "editor":
            status = "editor_approved"

        else:
            status = "submitted"

        article = Article.objects.create(
            title=title,
            content=content,
            category=category,
            reporter=request.user,
            edition=edition,
            status=status,
            edition_date=get_editorial_date()
        )

        ArticleActivity.objects.create(
            article=article,
            user=request.user,
            action=f"{role.capitalize()} created the article"
        )

        images = request.FILES.getlist("images")
        captions = request.POST.getlist("captions")

        for i,image in enumerate(images):

            caption = captions[i] if i < len(captions) else ""

            ArticleImage.objects.create(
                article=article,
                image=image,
                caption=caption
            )

        if role == "reporter":
            return redirect("/reporter-dashboard/")

        elif role == "subeditor":
            return redirect("/subeditor-dashboard/")

        elif role == "editor":
            return redirect("/editor-dashboard/")

    return render(request,"news/create_article.html",{
        "categories":categories
    })

#--------------------------------
# SEND TO OTHER EDITION
#--------------------------------

@login_required
def send_to_edition(request, article_id):

    article = Article.objects.get(id=article_id)

    if request.method == "POST":

        edition_id = request.POST.get("edition")

        edition = Edition.objects.get(id=edition_id)

        new_article = Article.objects.create(

            title=article.title,
            content=article.content,
            category=article.category,
            reporter=article.reporter,
            edition=edition,
            status="submitted",
            received_from_edition=True
        )

        # copy images

        images = ArticleImage.objects.filter(article=article)

        for img in images:

            ArticleImage.objects.create(
                article=new_article,
                image=img.image,
                caption=img.caption
            )

        ArticleActivity.objects.create(
            article=new_article,
            user=request.user,
            action=f"Story received from another edition ({article.edition.name})"
        )

        return redirect("/editor-dashboard/")

# -----------------------------------
# SUBEDITOR DASHBOARD
# -----------------------------------

@login_required
def subeditor_dashboard(request):

    edition = request.user.userprofile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status__in=["submitted","subeditor_review","editor_sent_back"]
    )

    search = request.GET.get("search")
    category = request.GET.get("category")
    status = request.GET.get("status")

    if search:

        articles = articles.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search)
        )

    if category:

        articles = articles.filter(category_id=category)

    if status:

        articles = articles.filter(status=status)

    categories = Category.objects.filter(edition=edition)

    new_articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="submitted"
    ).count()

    sent_back_articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="editor_sent_back"
    ).count()

    return render(request,"news/subeditor_dashboard.html",{
        "articles":articles,
        "categories":categories,
        "new_articles":new_articles,
        "sent_back_articles":sent_back_articles
    })



# -----------------------------------
# EDIT ARTICLE
# -----------------------------------

@login_required
def edit_article(request, article_id):

    article = Article.objects.get(id=article_id)

    if request.method == "POST":

        # Save previous version
        ArticleVersion.objects.create(
            article=article,
            title=article.title,
            content=article.content,
            edited_by=request.user
        )

        article.title = request.POST["title"]
        article.content = request.POST["content"]

        role = request.user.userprofile.role

        if role == "editor":

            page_number = request.POST.get("page_number")

            if not page_number:

                versions = article.versions.all().order_by("-edited_at")
                activities = article.activities.all().order_by("-created_at")
                editions = Edition.objects.exclude(id=article.edition.id)

                return render(request, "news/edit_article.html", {
                    "article": article,
                    "versions": versions,
                    "activities": activities,
                    "editions": editions,
                    "error": "Page number required"
                })

            article.page_number = int(page_number)
            article.status = "editor_approved"
            article.save()

            ArticleActivity.objects.create(
                article=article,
                user=request.user,
                action="Editor approved article"
            )

            return redirect("/editor-dashboard/")

        elif role == "subeditor":

            article.status = "subeditor_review"
            article.save()

            ArticleActivity.objects.create(
                article=article,
                user=request.user,
                action="SubEditor edited article"
            )

            return redirect("/subeditor-dashboard/")

    versions = article.versions.all().order_by("-edited_at")
    activities = article.activities.all().order_by("-created_at")

    # Send edition list to template (except current edition)
    editions = Edition.objects.exclude(id=article.edition.id)

    return render(request, "news/edit_article.html", {
        "article": article,
        "versions": versions,
        "activities": activities,
        "editions": editions
    })

# -----------------------------------
# EDITOR DASHBOARD
# -----------------------------------

@login_required
def editor_dashboard(request):

    edition = request.user.userprofile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="subeditor_review"
    )

    pending_articles = articles.count()

    return render(request,"news/editor_dashboard.html",{
        "articles":articles,
        "pending_articles":pending_articles
    })


# -----------------------------------
# APPROVE ARTICLE
# -----------------------------------

@login_required
def approve_article(request,article_id):

    article = Article.objects.get(id=article_id)

    if request.method == "POST":

        page = request.POST.get("page_number")

        article.page_number = int(page) if page else None
        article.status = "editor_approved"
        article.save()

        ArticleActivity.objects.create(
            article=article,
            user=request.user,
            action="Editor approved article"
        )

        return redirect("/editor-dashboard/")

    return render(request,"news/approve_article.html",{
        "article":article
    })


# -----------------------------------
# PAGINATION DASHBOARD
# -----------------------------------

@login_required
def pagination_dashboard(request):

    edition = request.user.userprofile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="editor_approved"
    )

    ready_for_pagination = articles.count()

    return render(request,"news/pagination_dashboard.html",{
        "articles":articles,
        "ready_for_pagination":ready_for_pagination
    })


# -----------------------------------
# PUBLISH ARTICLE
# -----------------------------------

@login_required
def publish_article(request,article_id):

    article = Article.objects.get(id=article_id)

    article.status = "published"
    article.save()

    ArticleActivity.objects.create(
        article=article,
        user=request.user,
        action="Paginator published article"
    )

    return redirect("/pagination-dashboard/")


# -----------------------------------
# SEND BACK TO SUBEDITOR
# -----------------------------------

@login_required
def send_back_to_subeditor(request, article_id):

    article = Article.objects.get(id=article_id)

    if request.method == "POST":

        comment = request.POST.get("editor_comment")

        article.editor_comment = comment
        article.status = "editor_sent_back"
        article.save()

        ArticleActivity.objects.create(
            article=article,
            user=request.user,
            action="Editor sent article back",
            comment=comment
        )

        return redirect("/editor-dashboard/")

    return render(request, "news/send_back.html", {
        "article": article
    })

# -----------------------------------
# RESTORE ARTICLE VERSION
# -----------------------------------

@login_required
def restore_version(request, version_id):

    version = ArticleVersion.objects.get(id=version_id)

    article = version.article

    # Save current version before restoring
    ArticleVersion.objects.create(
        article=article,
        title=article.title,
        content=article.content,
        edited_by=request.user
    )

    # Restore old content
    article.title = version.title
    article.content = version.content
    article.save()

    ArticleActivity.objects.create(
        article=article,
        user=request.user,
        action="Editor restored old article version"
    )

    return redirect(f"/edit-article/{article.id}/")


# -----------------------------------
# PAGE LAYOUT PLANNER
# -----------------------------------

from datetime import timedelta
from django.utils import timezone


@login_required
def page_layout_planner(request):

    page_number = int(request.GET.get("page", 1))

    now = timezone.localtime()

    # Production day logic (new edition day after 3AM)
    if now.hour < 3:
        production_date = (now - timedelta(days=1)).date()
    else:
        production_date = now.date()

    layouts = PageLayout.objects.filter(
        page_number=page_number,
        layout_date=production_date
    )

    layout_dict = {}

    for layout in layouts:
        layout_dict[layout.slot_number] = layout.article

    used_articles = layouts.values_list("article_id", flat=True)

    # Only today's approved stories
    articles = Article.objects.filter(
        status="editor_approved",
        page_number=page_number,
        created_at__date=production_date
    ).exclude(id__in=used_articles)

    return render(request, "news/page_layout_planner.html", {
        "articles": articles,
        "layouts": layout_dict,
        "page_number": page_number,
        "page_range": range(1, 17)   # 16 pages
    })


# -----------------------------------
# SAVE PAGE LAYOUT
# -----------------------------------

@login_required
def save_page_layout(request):

    if request.method == "POST":

        now = timezone.localtime()

        if now.hour < 3:
            production_date = (now - timedelta(days=1)).date()
        else:
            production_date = now.date()

        article_id = request.POST.get("article_id")
        slot_number = request.POST.get("slot_number")
        page_number = request.POST.get("page_number")

        article = Article.objects.get(id=article_id)

        PageLayout.objects.filter(
            page_number=page_number,
            slot_number=slot_number,
            layout_date=production_date
        ).delete()

        PageLayout.objects.create(
            page_number=page_number,
            slot_number=slot_number,
            article=article,
            layout_date=production_date
        )

        return JsonResponse({"status": "saved"})

# -----------------------------------
# EXPORT PAGE XML
# -----------------------------------

@login_required
def export_page_package(request,page_number):

    layouts = PageLayout.objects.filter(page_number=page_number)

    export_dir = f"/home/ubuntu/newsroom/exports/page_{page_number}"

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    zip_path = f"/home/ubuntu/newsroom/exports/page_{page_number}.zip"

    for layout in layouts:

        article = layout.article

        xml_file = f"{export_dir}/article_{article.id}.xml"

        root = ET.Element("article")

        ET.SubElement(root,"title").text = article.title
        ET.SubElement(root,"category").text = article.category.name
        ET.SubElement(root,"page").text = str(article.page_number)
        ET.SubElement(root,"reporter").text = article.reporter.username
        ET.SubElement(root,"content").text = article.content

        tree = ET.ElementTree(root)
        tree.write(xml_file)

    with zipfile.ZipFile(zip_path,'w') as zipf:

        for file in os.listdir(export_dir):

            zipf.write(
                os.path.join(export_dir,file),
                file
            )

    return FileResponse(open(zip_path,"rb"),as_attachment=True)


# -----------------------------------
# EXPORT SINGLE ARTICLE XML
# -----------------------------------

@login_required
def export_article_xml(request, article_id):

    article = Article.objects.get(id=article_id)

    export_dir = f"/home/ubuntu/newsroom/exports/article_{article.id}"

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    xml_file = os.path.join(export_dir, "article.xml")

    root = ET.Element("article")

    title = ET.SubElement(root, "title")
    title.text = article.title

    category = ET.SubElement(root, "category")
    category.text = article.category.name

    page = ET.SubElement(root, "page")
    page.text = str(article.page_number)

    reporter = ET.SubElement(root, "reporter")
    reporter.text = article.reporter.username

    content = ET.SubElement(root, "content")
    content.text = article.content

    images_node = ET.SubElement(root, "images")

    images = ArticleImage.objects.filter(article=article)

    for img in images:

        image_node = ET.SubElement(images_node, "image")

        file_node = ET.SubElement(image_node, "file")

        filename = os.path.basename(img.image.path)
        file_node.text = filename

        caption_node = ET.SubElement(image_node, "caption")
        caption_node.text = img.caption

        os.system(f"cp {img.image.path} {export_dir}/{filename}")

    tree = ET.ElementTree(root)
    tree.write(xml_file)

    zip_path = f"/home/ubuntu/newsroom/exports/article_{article.id}.zip"

    with zipfile.ZipFile(zip_path, 'w') as zipf:

        zipf.write(xml_file, "article.xml")

        for img in images:
            filename = os.path.basename(img.image.path)
            zipf.write(f"{export_dir}/{filename}", filename)

    return FileResponse(open(zip_path, 'rb'), as_attachment=True)

# -----------------------------------
# QUARK EXPORT
# -----------------------------------

@login_required
def export_quark_tagged_page(request,page_number):

    layouts = PageLayout.objects.filter(page_number=page_number)

    export_dir = f"/home/ubuntu/newsroom/exports/quark_page_{page_number}"

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    zip_path = f"/home/ubuntu/newsroom/exports/quark_page_{page_number}.zip"

    for layout in layouts:

        article = layout.article

        txt_file = f"{export_dir}/article_{article.id}.txt"

        with open(txt_file,"w") as f:

            f.write(f"<@Headline>{article.title}\n")
            f.write(f"<@Category>{article.category.name}\n")
            f.write(f"<@Reporter>{article.reporter.username}\n")
            f.write(f"<@BodyText>{article.content}\n")

            images = ArticleImage.objects.filter(article=article)

            for img in images:

                filename = os.path.basename(img.image.path)

                f.write(f"<@Caption>{img.caption}\n")

                os.system(f"cp {img.image.path} {export_dir}/{filename}")

    with zipfile.ZipFile(zip_path,'w') as zipf:

        for file in os.listdir(export_dir):

            zipf.write(
                os.path.join(export_dir,file),
                file
            )

    return FileResponse(open(zip_path,"rb"),as_attachment=True)


# -----------------------------------
# AI FUNCTIONS
# -----------------------------------

@login_required
def ai_improve_article(request):

    if request.method == "POST":

        text = request.POST.get("content")

        improved = improve_article(text)

        return JsonResponse({"improved_text":improved})


@login_required
def ai_generate_headline(request):

    if request.method == "POST":

        text = request.POST.get("content")

        headline = generate_headline(text)

        return JsonResponse({"headline":headline})


@login_required
def ai_generate_article(request):

    if request.method == "POST":

        notes = request.POST.get("notes")

        article = generate_article_from_notes(notes)

        return JsonResponse({"article":article})


# -----------------------------------
# ARCHIVE SEARCH
# -----------------------------------

@login_required
def archive_search(request):

    edition = request.user.userprofile.edition

    articles = Article.objects.filter(edition=edition)

    search = request.GET.get("search")
    category = request.GET.get("category")
    reporter = request.GET.get("reporter")
    date = request.GET.get("date")

    if search:
        articles = articles.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search)
        )

    if category:
        articles = articles.filter(category_id=category)

    if reporter:
        articles = articles.filter(reporter__username__icontains=reporter)

    if date:
        articles = articles.filter(edition_date=date)

    categories = Category.objects.filter(edition=edition)

    return render(request,"news/archive_search.html",{
        "articles":articles.order_by("-edition_date"),
        "categories":categories
    })


#----------------------
#EDITION INBOX VIEW
#----------------------
@login_required
def edition_inbox(request):

    user_edition = request.user.userprofile.edition

    articles = Article.objects.filter(
        edition=user_edition,
        received_from_edition=True,
        status="submitted"
    )

    return render(request,"news/edition_inbox.html",{
        "articles":articles
    })


#-------------------------
#CHANGE PASSWORD
#-------------------------
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(request, user)

            return redirect("/")

    else:

        form = PasswordChangeForm(request.user)

    return render(request, "news/change_password.html", {
        "form": form
    })

#------------------
#LOGIN REDIRECT
#------------------
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def login_redirect(request):

    profile = request.user.userprofile

    # Force password change
    if profile.must_change_password:
        return redirect("/change-password/")

    role = profile.role

    if role == "reporter":
        return redirect("/reporter-dashboard/")

    elif role == "subeditor":
        return redirect("/subeditor-dashboard/")

    elif role == "editor":
        return redirect("/editor-dashboard/")

    elif role == "paginator":
        return redirect("/pagination-dashboard/")

    return redirect("/")
