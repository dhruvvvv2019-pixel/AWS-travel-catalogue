# AWS Travel Catalogue — Cloud-Native Web Application

A containerized Flask web application deployed on Amazon EC2 with DynamoDB for persistent destination data, Amazon S3 for private image storage, and Amazon SNS for event-driven email notifications.

| | |
|---|---|
| **Student** | Dhruv Mishra |
| **Course** | Cloud Computing |
| **AWS Region** | eu-north-1 (Europe/Stockholm) |
| **Live App** | [http://16.171.136.32](http://16.171.136.32) |

---

## Overview

**Travel Catalogue** is a cloud-hosted web application for storing and browsing travel destinations. Users can:

- Add a new destination
- View all stored destinations
- Filter destinations by country, category, or budget
- Open a destination's detail page
- Upload an image for a destination
- Delete a destination

The app is built with **Flask**, served via **Gunicorn**, and runs inside a **Docker** container on **Amazon EC2**. Destination records are stored in **DynamoDB**, images are stored in a private **S3** bucket, and an **SNS** topic emails a notification every time a new destination is added.

---

## AWS Services Used

| Service | Purpose |
|---|---|
| **Amazon EC2** | Runs the Dockerized Flask/Gunicorn app, exposed publicly on HTTP port 80. |
| **Amazon DynamoDB** | Stores travel destination records (`destination_id` as partition key). |
| **Amazon S3** | Stores uploaded destination images in a private bucket. |
| **Amazon SNS** | Publishes a notification to a confirmed email subscription after a destination is added. |
| **AWS IAM** | Grants the EC2 instance scoped permissions to DynamoDB, S3, and SNS — no hard-coded credentials. |

---

## Architecture

```
                    ┌────────────────────┐
   Internet /  ───▶ │   EC2 Instance      │
   Public Users     │  ┌──────────────┐   │
                    │  │ Docker        │   │
                    │  │ Flask+Gunicorn│   │
                    │  └──────┬───────┘   │
                    └─────────┼───────────┘
                              │
           ┌──────────────┬──┴───────────┬──────────────┐
           ▼              ▼              ▼
      DynamoDB          S3 (private)     SNS
   (destination data)  (images)      (email alerts)
```

The EC2 instance authenticates to AWS using an **IAM role** — no access keys are stored in the container or codebase.

---

## Live Demo — Public Deployment

The fastest way to see the app working is through the public EC2 address.

1. Open a browser and navigate to **http://16.171.136.32**
2. The Travel Catalogue home page loads, showing stored destinations and filter controls
3. Click **+ Add Destination** to test the create flow
4. Enter name, country, city, category, a positive whole-number budget, description, and optionally an image
5. Click **Add Destination** — a success message appears and the new entry shows up in the catalogue
6. Click **View** on a destination to open its detail page (images are pulled from the private S3 bucket)
7. Return home and try the **country**, **category**, and **max budget** filters
8. Submit incomplete/invalid data to confirm validation errors appear instead of a saved record
9. Check the subscribed email inbox — SNS should deliver a message with the destination, country, city, category, and budget

> **Note on the public URL:** Since an Elastic IP is not used, the EC2 public IPv4 address can change if the instance is stopped and restarted. If `16.171.136.32` no longer works, check the current **Public IPv4** value in the EC2 console.

---

## Verifying the AWS Backend

| Service | How to check |
|---|---|
| **DynamoDB** | Console → DynamoDB → Tables → `ELL82287-TravelDestinations` — should be `Active` with created records. |
| **S3** | Console → S3 → bucket `ell82287-travel-catalogue-images-2026` — uploaded images appear here (bucket is private). |
| **SNS** | Console → SNS → Topics → `ELL82287-TravelCatalogue-Notifications` — has a confirmed email subscription. |
| **EC2** | Console → EC2 → Instances → `ELL82287-TravelCatalogue-Server` — `t3.micro`, Amazon Linux 2023, Docker maps host port 80 → container port 5000. |
| **IAM** | Instance uses role `ELL82287-TravelCatalogue-EC2-Role` — no AWS keys required in the app. |

---

## Local Setup (Optional)

The public deployment is the recommended way to demo the project, but it can also be run locally.

```bash
# 1. Open the project
cd ~/ell82287-assignment/assignment-2

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then fill in a valid Flask secret and, if running outside EC2, valid AWS credentials

# 5. Start Flask
python run.py
```

Then open the local address printed by Flask (typically `http://127.0.0.1:5000`).

---

## Docker Deployment

The project ships with a `Dockerfile` based on **Python 3.13** that installs dependencies, copies the app, and runs it with **Gunicorn (2 workers)**.

```bash
# Build the image
docker build -t travel-catalogue:latest .

# Run locally
docker run --env-file .env -p 5000:5000 travel-catalogue:latest
```

In the cloud deployment, the image is pulled from Docker Hub and run on EC2. The EC2 **IAM role** supplies AWS permissions, so no credentials are mounted into the container.

---

## Features to Demonstrate

| Feature | Action |
|---|---|
| Add destination | Use **+ Add Destination** and submit valid details |
| List destinations | Open the home page |
| Filter by country | Select a country → **Filter** |
| Filter by category | Select a category → **Filter** |
| Filter by budget | Enter a max budget → **Filter** |
| Destination details | Click **View** on a card |
| S3 image | Add a destination with an image, then view its detail page |
| Invalid input | Submit missing/invalid fields, check validation |
| Delete | Open a destination → **Delete Destination** |
| SNS notification | Add a destination, check subscribed email inbox |

---

## Source Code Structure

```
assignment-2/
├── app/
│   ├── __init__.py
│   ├── aws_services.py
│   ├── config.py
│   ├── routes.py
│   ├── static/
│   └── templates/
├── tests/
├── Dockerfile
├── requirements.txt
├── run.py
├── .dockerignore
├── .gitignore
└── .env.example
```

> The actual `.env` file is **not** included in this submission since it contains the production Flask secret and deployment configuration. `.env.example` is provided as a safe template.

---

## Security Notes

- The S3 bucket is private with public access blocked.
- Uploaded images are fetched by Flask from S3 and served through the app (never public S3 URLs).
- EC2 uses an **IAM role** instead of embedded AWS access keys.
- The production Flask secret is supplied via environment variable.
- Input validation rejects invalid destination data and unsupported image types.
- The SSH security-group rule is restricted to the developer's current IP; only HTTP port 80 is publicly open for the demo.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Public page won't open | Confirm the EC2 instance is `Running`, the Docker container is `Up`, and the security group allows inbound TCP 80 |
| SSH doesn't work | Security group SSH rule is IP-restricted — update the source rule if your network IP changed |
| Images don't display | Check the destination has an `image_key` and the EC2 IAM role has `s3:GetObject` permission |
| Destination won't save | Check DynamoDB permissions and the table name/region in the environment config |
| No email notification | Confirm the SNS subscription is confirmed and the topic ARN is correct |
| Health check | On EC2: `curl http://localhost/health` → should return `OK` |

---

## Quick Demo Sequence

1. Open the public URL and show the catalogue
2. Add a new destination with an image
3. Show the success message and new entry
4. Open the destination detail page and show the image
5. Apply a country/category/budget filter
6. Submit invalid input and show the validation error
7. Show the SNS email notification received after the add
8. (Optional) Show the DynamoDB item and S3 object in the AWS console
