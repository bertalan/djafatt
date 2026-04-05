"""Configure webhook URL on OpenAPI SDI service."""

from django.core.management.base import BaseCommand

from apps.sdi.services.openapi_client import OpenApiSdiClient


class Command(BaseCommand):
    help = "Register webhook URL with OpenAPI SDI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default="https://fatt.betabi.it/webhooks/sdi/",
            help="Webhook callback URL",
        )

    def handle(self, *args, **options):
        url = options["url"]
        client = OpenApiSdiClient()
        self.stdout.write(f"Configuring webhook URL: {url}")
        self.stdout.write(f"Endpoint: {client.base_url}")
        result = client.configure_webhooks(url)
        self.stdout.write(self.style.SUCCESS(f"Done: {result}"))
