import os

from botocore.exceptions import ClientError
from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.aws_services import (
    create_destination,
    delete_destination,
    get_destination,
    get_image,
    list_destinations,
)

main = Blueprint("main", __name__)

ALLOWED_CATEGORIES = {
    "Beach",
    "Mountain",
    "City",
    "Historical",
    "Adventure",
    "Wildlife",
    "Other",
}

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_image(image_file):
    """Validate an uploaded image."""
    if not image_file or not image_file.filename:
        return None

    filename = image_file.filename.strip()

    if "." not in filename:
        return "Image must have a valid extension."

    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return "Only JPG, JPEG, PNG, and WEBP images are allowed."

    image_file.seek(0, os.SEEK_END)
    size = image_file.tell()
    image_file.seek(0)

    if size > MAX_IMAGE_SIZE:
        return "Image size must be 5 MB or less."

    return None


def validate_destination_form(form):
    """Validate destination form fields."""
    errors = {}

    name = form.get("name", "").strip()
    country = form.get("country", "").strip()
    city = form.get("city", "").strip()
    category = form.get("category", "").strip()
    description = form.get("description", "").strip()
    budget_raw = form.get("budget", "").strip()

    if not name:
        errors["name"] = "Destination name is required."
    elif not 2 <= len(name) <= 100:
        errors["name"] = "Name must be between 2 and 100 characters."

    if not country:
        errors["country"] = "Country is required."
    elif not 2 <= len(country) <= 60:
        errors["country"] = "Country must be between 2 and 60 characters."

    if not city:
        errors["city"] = "City is required."
    elif not 2 <= len(city) <= 60:
        errors["city"] = "City must be between 2 and 60 characters."

    if category not in ALLOWED_CATEGORIES:
        errors["category"] = "Please select a valid category."

    if not description:
        errors["description"] = "Description is required."
    elif not 10 <= len(description) <= 1000:
        errors["description"] = (
            "Description must be between 10 and 1000 characters."
        )

    if not budget_raw:
        errors["budget"] = "Budget is required."
    else:
        try:
            budget = int(budget_raw)

            if budget <= 0:
                errors["budget"] = "Budget must be greater than zero."

        except ValueError:
            errors["budget"] = "Budget must be a whole number."

    return errors


@main.route("/")
def index():
    """Display all destinations and apply optional filters."""

    try:
        destinations = list_destinations()

    except ClientError:
        flash(
            "Unable to retrieve destinations right now.",
            "error",
        )
        destinations = []

    country_filter = request.args.get(
        "country",
        "",
    ).strip()

    category_filter = request.args.get(
        "category",
        "",
    ).strip()

    max_budget_raw = request.args.get(
        "max_budget",
        "",
    ).strip()

    max_budget = None

    if max_budget_raw:
        try:
            max_budget = int(max_budget_raw)

            if max_budget < 0:
                flash(
                    "Maximum budget cannot be negative.",
                    "error",
                )
                max_budget = None

        except ValueError:
            flash(
                "Maximum budget must be a valid number.",
                "error",
            )

    filtered_destinations = []

    for destination in destinations:
        country = str(
            destination.get("country", "")
        )

        category = str(
            destination.get("category", "")
        )

        try:
            budget = int(
                destination.get("budget", 0)
            )
        except (TypeError, ValueError):
            budget = 0

        if country_filter:
            if country.lower() != country_filter.lower():
                continue

        if category_filter:
            if category.lower() != category_filter.lower():
                continue

        if max_budget is not None:
            if budget > max_budget:
                continue

        filtered_destinations.append(destination)

    return render_template(
        "index.html",
        destinations=filtered_destinations,
        country_filter=country_filter,
        category_filter=category_filter,
        max_budget=max_budget_raw,
        categories=sorted(ALLOWED_CATEGORIES),
    )


@main.route("/add", methods=["GET", "POST"])
def add_destination():
    """Display and process the add-destination form."""

    if request.method == "GET":
        return render_template(
            "add.html",
            categories=sorted(ALLOWED_CATEGORIES),
            form={},
        )

    errors = validate_destination_form(request.form)

    image_file = request.files.get("image")

    image_error = validate_image(image_file)

    if image_error:
        errors["image"] = image_error

    if errors:
        for message in errors.values():
            flash(message, "error")

        return render_template(
            "add.html",
            categories=sorted(ALLOWED_CATEGORIES),
            form=request.form,
        ), 400

    name = request.form["name"].strip()
    country = request.form["country"].strip()
    city = request.form["city"].strip()
    category = request.form["category"].strip()
    description = request.form["description"].strip()
    budget = int(request.form["budget"].strip())

    try:
        destination = create_destination(
            name=name,
            country=country,
            city=city,
            category=category,
            description=description,
            budget=budget,
            image_file=image_file,
        )

        flash(
            f"Destination '{destination['name']}' added successfully.",
            "success",
        )

        return redirect(
            url_for("main.index")
        )

    except ClientError:
        flash(
            "Unable to save the destination. "
            "Please check the AWS services and try again.",
            "error",
        )

        return render_template(
            "add.html",
            categories=sorted(ALLOWED_CATEGORIES),
            form=request.form,
        ), 500

    except (TypeError, ValueError):
        flash(
            "Invalid destination data.",
            "error",
        )

        return render_template(
            "add.html",
            categories=sorted(ALLOWED_CATEGORIES),
            form=request.form,
        ), 400


@main.route("/destination/<destination_id>")
def destination_detail(destination_id):
    """Display details for one destination."""

    try:
        destination = get_destination(destination_id)

    except ClientError:
        flash(
            "Unable to retrieve this destination right now.",
            "error",
        )
        return redirect(url_for("main.index"))

    if not destination:
        flash(
            "Destination not found.",
            "error",
        )
        return redirect(url_for("main.index"))

    return render_template(
        "detail.html",
        destination=destination,
    )


@main.route("/image/<destination_id>")
def destination_image(destination_id):
    """
    Securely serve a private S3 image through Flask.

    The browser never receives AWS credentials and the S3
    bucket can remain private.
    """

    try:
        destination = get_destination(destination_id)

        if not destination:
            return "Image not found", 404

        image_key = destination.get("image_key")

        if not image_key:
            return "Image not found", 404

        image_data, content_type = get_image(image_key)

        if not image_data:
            return "Image not found", 404

        return Response(
            image_data,
            mimetype=content_type,
            headers={
                "Cache-Control": "private, max-age=3600",
            },
        )

    except ClientError:
        return "Image unavailable", 404

    except Exception:
        return "Image unavailable", 404


@main.route(
    "/delete/<destination_id>",
    methods=["POST"],
)
def delete_destination_route(destination_id):
    """Delete a destination and its S3 image."""

    try:
        deleted = delete_destination(destination_id)

    except ClientError:
        flash(
            "Unable to delete the destination right now.",
            "error",
        )
        return redirect(url_for("main.index"))

    if deleted:
        flash(
            "Destination deleted successfully.",
            "success",
        )
    else:
        flash(
            "Destination not found.",
            "error",
        )

    return redirect(
        url_for("main.index")
    )


@main.route("/health")
def health():
    """Simple health-check endpoint."""

    return "OK", 200