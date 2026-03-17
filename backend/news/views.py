import os
import zipfile
import xml.etree.ElementTree as ET

from .utils import get_editorial_date
from django.utils import timezone
from datetime import timedelta
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

from .ai_services import (
    improve_article,
    generate_headline,
    generate_article_from_notes,
    create_article_from_topic
)

# -----------------------------------
# REPORTER DASHBOARD
# -----------------------------------

@login_required
def reporter_dashboard(request):

    profile = request.user.userprofile
    edition = profile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        reporter=request.user,
        edition=edition,
        edition_date=today
    )

    context = {
        "articles": articles,

        # Role flags for navbar
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/reporter_dashboard.html", context)

# -----------------------------------
# CREATE ARTICLE
# -----------------------------------

@login_required
def create_article(request):

    profile = request.user.userprofile
    edition = profile.edition

    categories = Category.objects.filter(edition=edition)

    if request.method == "POST":

        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category")

        category = Category.objects.filter(id=category_id).first()

        if not category:
            return redirect("/create-article/")

        # Determine role priority
        if profile.has_role("Editor"):
            role = "editor"
            status = "subeditor_review"

        elif profile.has_role("SubEditor"):
            role = "subeditor"
            status = "subeditor_review"

        elif profile.has_role("Reporter"):
            role = "reporter"
            status = "submitted"

        else:
            role = "reporter"
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

        for i, image in enumerate(images):

            caption = captions[i] if i < len(captions) else ""

            ArticleImage.objects.create(
                article=article,
                image=image,
                caption=caption
            )

        # Redirect based on highest role
        if profile.has_role("Editor"):
            return redirect("/editor-dashboard/")

        elif profile.has_role("SubEditor"):
            return redirect("/subeditor-dashboard/")

        else:
            return redirect("/reporter-dashboard/")

    context = {
        "categories": categories,

        # Navbar role flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/create_article.html", context)


#--------------------------------
# SEND TO OTHER EDITION
#--------------------------------

@login_required
def send_to_edition(request, article_id):

    profile = request.user.userprofile

    # Only editors can send stories to other editions
    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

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
            received_from_edition=True,
            edition_date=get_editorial_date()
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

    context = {
        "article": article,

        # Navbar role flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/send_to_edition.html", context)


# -----------------------------------
# SUBEDITOR DASHBOARD
# -----------------------------------

@login_required
def subeditor_dashboard(request):

    profile = request.user.userprofile
    edition = profile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status__in=["submitted", "subeditor_review", "editor_sent_back"]
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

    context = {

        "articles": articles,
        "categories": categories,
        "new_articles": new_articles,
        "sent_back_articles": sent_back_articles,

        # Role flags for navbar
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/subeditor_dashboard.html", context)


# -----------------------------------
# EDIT ARTICLE
# -----------------------------------

@login_required
def edit_article(request, article_id):

    profile = request.user.userprofile
    article = Article.objects.get(id=article_id)

    # 🔥 Prepare editions (user edition first)
    user_edition = profile.edition

    if user_edition:
        editions = [user_edition] + list(
            Edition.objects.exclude(id=user_edition.id)
        )
    else:
        editions = Edition.objects.all()

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

        # ----------------------------
        # EDITOR ROLE
        # ----------------------------
        if profile.has_role("Editor"):

            page_number = request.POST.get("page_number")
            edition_id = request.POST.get("edition")

            if not page_number:

                versions = article.versions.all().order_by("-edited_at")
                activities = article.activities.all().order_by("-created_at")

                context = {
                    "article": article,
                    "versions": versions,
                    "activities": activities,
                    "editions": editions,
                    "user_edition": user_edition,
                    "error": "Page number required",

                    # Navbar flags
                    "can_create_article": (
                        profile.has_role("Reporter") or
                        profile.has_role("SubEditor") or
                        profile.has_role("Editor")
                    ),
                    "can_page_plan": (
                        profile.has_role("Editor") or
                        profile.has_role("Paginator")
                    ),
                    "is_editor": profile.has_role("Editor"),
                }

                return render(request, "news/edit_article.html", context)

            # ✅ Save page number
            article.page_number = int(page_number)

            # 🔥 IMPORTANT FIX: Save selected edition
            if edition_id:
                article.edition = Edition.objects.get(id=edition_id)

            article.status = "editor_approved"
            article.save()

            ArticleActivity.objects.create(
                article=article,
                user=request.user,
                action="Editor approved article"
            )

            return redirect("/editor-dashboard/")

        # ----------------------------
        # SUBEDITOR ROLE
        # ----------------------------
        elif profile.has_role("SubEditor"):

            article.status = "subeditor_review"
            article.save()

            ArticleActivity.objects.create(
                article=article,
                user=request.user,
                action="SubEditor edited article"
            )

            return redirect("/subeditor-dashboard/")

    # ----------------------------
    # GET REQUEST
    # ----------------------------

    versions = article.versions.all().order_by("-edited_at")
    activities = article.activities.all().order_by("-created_at")

    context = {
        "article": article,
        "versions": versions,
        "activities": activities,
        "editions": editions,
        "user_edition": user_edition,

        # Navbar flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/edit_article.html", context)


# -----------------------------------
# EDITOR DASHBOARD
# -----------------------------------

@login_required
def editor_dashboard(request):

    profile = request.user.userprofile
    edition = profile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="subeditor_review"
    )

    pending_articles = articles.count()

    # Role flags for navbar
    context = {
        "articles": articles,
        "pending_articles": pending_articles,

        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/editor_dashboard.html", context)

# -----------------------------------
# APPROVE ARTICLE
# -----------------------------------

@login_required
def approve_article(request, article_id):

    profile = request.user.userprofile

    # Only editors can approve
    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

    article = Article.objects.get(id=article_id)

    # 🔥 FIX: Put user's edition first
    user_edition = profile.edition

    if user_edition:
        editions = [user_edition] + list(
            Edition.objects.exclude(id=user_edition.id)
        )
    else:
        editions = Edition.objects.all()

    if request.method == "POST":

        page = request.POST.get("page_number")
        edition_id = request.POST.get("edition")

        # Assign page
        article.page_number = int(page) if page else None

        # Assign edition
        if edition_id:
            article.edition = Edition.objects.get(id=edition_id)

        article.status = "editor_approved"
        article.save()

        ArticleActivity.objects.create(
            article=article,
            user=request.user,
            action="Editor approved article"
        )

        return redirect("/editor-dashboard/")

    context = {
        "article": article,
        "editions": editions,
        "user_edition": user_edition,   # still useful if needed later

        # Navbar role flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/approve_article.html", context)

# -----------------------------------
# PAGINATION DASHBOARD
# -----------------------------------

@login_required
def pagination_dashboard(request):

    profile = request.user.userprofile
    edition = profile.edition
    today = get_editorial_date()

    articles = Article.objects.filter(
        edition=edition,
        edition_date=today,
        status="editor_approved"
    )

    ready_for_pagination = articles.count()

    context = {
        "articles": articles,
        "ready_for_pagination": ready_for_pagination,

        # Role flags for navbar
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/pagination_dashboard.html", context)


# -----------------------------------
# PUBLISH ARTICLE
# -----------------------------------

@login_required
def publish_article(request, article_id):

    profile = request.user.userprofile

    # Only paginator can publish
    if not profile.has_role("Paginator"):
        return redirect("/login-redirect/")

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

    profile = request.user.userprofile

    # Only editor allowed
    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

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

    # GET request → show form
    return render(request, "news/send_back.html", {
        "article": article
    })


# -----------------------------------
# RESTORE ARTICLE VERSION
# -----------------------------------

@login_required
def restore_version(request, version_id):

    profile = request.user.userprofile

    # Only editor can restore versions
    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

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

@login_required
def page_layout_planner(request):

    profile = request.user.userprofile

    # Only Editor or Paginator allowed
    if not (profile.has_role("Editor") or profile.has_role("Paginator")):
        return redirect("/login-redirect/")

    edition = profile.edition
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

    # Only today's approved stories of this edition
    articles = Article.objects.filter(
        edition=edition,
        edition_date=production_date,
        status="editor_approved",
        page_number=page_number
    ).exclude(id__in=used_articles)

    context = {
        "articles": articles,
        "layouts": layout_dict,
        "page_number": page_number,
        "page_range": range(1, 17),

        # Navbar flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/page_layout_planner.html", context)


# -----------------------------------
# SAVE PAGE LAYOUT
# -----------------------------------

@login_required
def save_page_layout(request):

    profile = request.user.userprofile

    if not (profile.has_role("Editor") or profile.has_role("Paginator")):
        return JsonResponse({"status": "error", "message": "Permission denied"})

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

#--------------------
# EXPORT PAGE XML
# -------------------
@login_required
def export_page_package(request, page_number):

    profile = request.user.userprofile

    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

    layouts = PageLayout.objects.filter(page_number=page_number)

    export_dir = f"/home/ubuntu/newsroom/exports/page_{page_number}"

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    zip_path = f"/home/ubuntu/newsroom/exports/page_{page_number}.zip"

    for layout in layouts:

        article = layout.article

        xml_file = f"{export_dir}/article_{article.id}.xml"

        root = ET.Element("article")

        ET.SubElement(root, "title").text = article.title
        ET.SubElement(root, "category").text = article.category.name
        ET.SubElement(root, "page").text = str(article.page_number)
        ET.SubElement(root, "reporter").text = article.reporter.username
        ET.SubElement(root, "content").text = article.content

        tree = ET.ElementTree(root)
        tree.write(xml_file)

    with zipfile.ZipFile(zip_path, 'w') as zipf:

        for file in os.listdir(export_dir):

            zipf.write(
                os.path.join(export_dir, file),
                file
            )

    return FileResponse(open(zip_path, "rb"), as_attachment=True)

# -----------------------------------
# EXPORT SINGLE ARTICLE XML
# -----------------------------------

@login_required
def export_article_xml(request, article_id):

    profile = request.user.userprofile

    if not (profile.has_role("Editor") or profile.has_role("Paginator")):
        return redirect("/login-redirect/")

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
def export_quark_tagged_page(request, page_number):

    profile = request.user.userprofile

    if not profile.has_role("Paginator"):
        return redirect("/login-redirect/")

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


@login_required
def ai_generate_topic_article(request):

    if request.method == "POST":

        topic = request.POST.get("topic")

        result = create_article_from_topic(topic)

        return JsonResponse(result)

    return JsonResponse({"error": "POST request required"})

# -----------------------------------
# POWERFUL NEWSROOM ARCHIVE SEARCH
# -----------------------------------

@login_required
def archive_search(request):

    profile = request.user.userprofile
    edition = profile.edition

    articles = Article.objects.filter(edition=edition)

    # Filters from search form
    search = request.GET.get("search")
    category = request.GET.get("category")
    reporter = request.GET.get("reporter")
    date = request.GET.get("date")
    status = request.GET.get("status")

    # Keyword search
    if search:
        articles = articles.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search)
        )

    # Category filter
    if category:
        articles = articles.filter(category_id=category)

    # Reporter filter
    if reporter:
        articles = articles.filter(reporter__username__icontains=reporter)

    # Date filter
    if date:
        articles = articles.filter(edition_date=date)

    # Status filter
    if status:
        articles = articles.filter(status=status)

    # Order latest first
    articles = articles.order_by("-edition_date", "-created_at")

    categories = Category.objects.filter(edition=edition)

    context = {

        "articles": articles,
        "categories": categories,

        "search": search,
        "reporter": reporter,
        "date": date,
        "status": status,
        "selected_category": category,

        # Navbar flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),

        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),

        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/archive_search.html", context)

#----------------------
# EDITION INBOX VIEW
#----------------------

@login_required
def edition_inbox(request):

    profile = request.user.userprofile

    # Only editors can access inbox
    if not profile.has_role("Editor"):
        return redirect("/login-redirect/")

    user_edition = profile.edition

    articles = Article.objects.filter(
        edition=user_edition,
        received_from_edition=True,
        status="submitted"
    )

    context = {
        "articles": articles,

        # Navbar flags
        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),
        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),
        "is_editor": profile.has_role("Editor"),
    }

    return render(request,"news/edition_inbox.html", context)



#-------------------------
# CHANGE PASSWORD
#-------------------------

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


@login_required
def change_password(request):

    profile = request.user.userprofile

    if request.method == "POST":

        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(request, user)

            # Remove force password change flag
            profile.must_change_password = False
            profile.save()

            return redirect("/login-redirect/")

    else:

        form = PasswordChangeForm(request.user)

    context = {
        "form": form,

        "can_create_article": (
            profile.has_role("Reporter") or
            profile.has_role("SubEditor") or
            profile.has_role("Editor")
        ),
        "can_page_plan": (
            profile.has_role("Editor") or
            profile.has_role("Paginator")
        ),
        "is_editor": profile.has_role("Editor"),
    }

    return render(request, "news/change_password.html", context)


#------------------
# LOGIN REDIRECT
#------------------

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile


@login_required
def login_redirect(request):

    user = request.user

    # Superuser → User Control Panel
    if user.is_superuser:
        return redirect("/user-control/")

    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    # Force password change
    if profile.must_change_password:
        return redirect("/change-password/")

    roles = profile.roles.all()

    # Priority order
    if roles.filter(name="Editor").exists():
        return redirect("/editor-dashboard/")

    elif roles.filter(name="SubEditor").exists():
        return redirect("/subeditor-dashboard/")

    elif roles.filter(name="Paginator").exists():
        return redirect("/pagination-dashboard/")

    elif roles.filter(name="Reporter").exists():
        return redirect("/reporter-dashboard/")

    return redirect("/")

#--------------------
# ADMIN VIEW
#-------------------

from django.contrib.auth.models import User
from accounts.models import UserProfile


@login_required
def user_control_panel(request):

    if not request.user.is_superuser:
        return redirect("/")

    users = User.objects.all().order_by("username")

    user_data = []

    for user in users:

        try:
            profile = user.userprofile
        except UserProfile.DoesNotExist:
            profile = None

        user_data.append({
            "user": user,
            "profile": profile
        })

    return render(request, "news/user_control_panel.html", {
        "user_data": user_data
    })

#------------------
# CREATE USER
#------------------

from django.contrib.auth.models import User
from accounts.models import UserProfile, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Edition


@login_required
def create_user(request):

    if not request.user.is_superuser:
        return redirect("/")

    editions = Edition.objects.all()
    roles = Role.objects.all()

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role_ids = request.POST.getlist("roles")   # MULTI ROLE
        edition_id = request.POST.get("edition")

        # Prevent duplicate username
        if User.objects.filter(username=username).exists():

            return render(request, "news/create_user.html", {
                "editions": editions,
                "roles": roles,
                "error": "Username already exists"
            })

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Get profile (created automatically by signal)
        profile = user.userprofile

        # Assign edition
        if edition_id:
            profile.edition = Edition.objects.get(id=edition_id)

        profile.must_change_password = True
        profile.save()

        # Assign MULTIPLE roles
        if role_ids:

            selected_roles = Role.objects.filter(id__in=role_ids)

            for role in selected_roles:
                profile.roles.add(role)

        return redirect("/user-control/")

    return render(request, "news/create_user.html", {
        "editions": editions,
        "roles": roles
    })

#--------------
# EDIT USER
#--------------

@login_required
def edit_user(request, user_id):

    if not request.user.is_superuser:
        return redirect("/")

    from django.contrib.auth.models import User
    from accounts.models import UserProfile, Role
    from .models import Edition

    user = User.objects.get(id=user_id)
    profile = user.userprofile

    editions = Edition.objects.all()
    roles = Role.objects.all()

    if request.method == "POST":

        role_ids = request.POST.getlist("roles")   # MULTI ROLE
        edition_id = request.POST.get("edition")

        # Update roles
        if role_ids:
            selected_roles = Role.objects.filter(id__in=role_ids)
            profile.roles.set(selected_roles)   # replace existing roles

        # Update edition
        if edition_id:
            profile.edition = Edition.objects.get(id=edition_id)
        else:
            profile.edition = None

        profile.save()

        return redirect("/user-control/")

    return render(request, "news/edit_user.html", {
        "user_obj": user,
        "profile": profile,
        "editions": editions,
        "roles": roles
    })


#---------------------
# ENABLE / DISABLE USER
#---------------------
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


@login_required
def toggle_user(request, user_id):

    if not request.user.is_superuser:
        return redirect("/")

    user = get_object_or_404(User, id=user_id)

    # Prevent admin disabling himself
    if user == request.user:
        return redirect("/user-control/")

    user.is_active = not user.is_active
    user.save()

    return redirect("/user-control/")


#----------------
# RESET PASSWORD
#----------------
@login_required
def reset_password(request, user_id):

    if not request.user.is_superuser:
        return redirect("/")

    user = get_object_or_404(User, id=user_id)

    # Default newsroom reset password
    user.set_password("newsroom123")
    user.save()

    profile = user.userprofile
    profile.must_change_password = True
    profile.save()

    return redirect("/user-control/")
