from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from papers.models import Paper


class Command(BaseCommand):
    help = "Cria um usuário demo sem privilégios e dois resumos fictícios."

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username="demo").first()
        if user is None:
            user = get_user_model()(username="demo")
            password = getpass("Escolha uma senha para demo (não será exibida): ")
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise CommandError("; ".join(exc.messages)) from exc
            user.set_password(password)
            user.save()
        examples = [
            (
                "Clareza na comunicação científica",
                "Este estudo avalia a a clareza de resumos científicos em português. A análise compara versões de textos para identificar oportunidades de melhoria na comunicação dos resultados.",
            ),
            (
                "Reprodutibilidade em pesquisa",
                "Este trabalho apresenta um protocolo de organização de dados experimentais. O método utiliza registros versionados para facilitar a reprodução dos resultados por outros pesquisadores.",
            ),
        ]
        for title, abstract in examples:
            Paper.objects.get_or_create(owner=user, title=title, defaults={"abstract": abstract})
        self.stdout.write(self.style.SUCCESS("Dados disponíveis. Entre na API com o usuário demo."))
