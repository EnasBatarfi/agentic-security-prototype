from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create a superuser + 2 demo users (safe for local dev)."

    def handle(self, *args, **options):
        User = get_user_model()

        users_to_seed = [
            # username, password, is_superuser, is_staff
            ("admin", "admin12345", True, True),
            ("user1", "user12345", False, False),
            ("user2", "user12345", False, False),
        ]

        for username, password, is_super, is_staff in users_to_seed:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.is_superuser = is_super
            user.is_staff = is_staff
            user.is_active = True
            user.save()

            status = "CREATED" if created else "UPDATED"
            self.stdout.write(self.style.SUCCESS(f"{status}: {username}"))

        self.stdout.write(self.style.SUCCESS("Done."))
