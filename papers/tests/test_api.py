from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from papers.models import Paper, Review
from papers.services import analyze_text, review_paper


class PaperAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("arthur", password="test-password-871")
        self.other = get_user_model().objects.create_user("other", password="other-password-871")
        self.paper = Paper.objects.create(
            owner=self.user,
            title="Pesquisa",
            abstract="Este estudo analisa a a comunicação científica.",
        )
        self.foreign = Paper.objects.create(
            owner=self.other, title="Privado", abstract="Este resumo pertence a outro pesquisador."
        )
        self.client.force_authenticate(self.user)

    def test_anonymous_cannot_access_api(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/papers/").status_code, 401)

    def test_list_only_returns_own_papers(self):
        response = self.client.get("/api/papers/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.paper.pk)

    def test_foreign_paper_is_hidden_for_every_action(self):
        url = f"/api/papers/{self.foreign.pk}/"
        for method, endpoint, data in [
            ("get", url, None),
            ("patch", url, {"title": "Alterado"}),
            ("put", url, {"title": "Alterado", "abstract": "Um resumo com cinco palavras."}),
            ("delete", url, None),
            ("post", url + "review/", {}),
            ("get", url + "reviews/", None),
        ]:
            with self.subTest(method=method, endpoint=endpoint):
                self.assertEqual(getattr(self.client, method)(endpoint, data=data).status_code, 404)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.title, "Privado")

    def test_owner_cannot_be_forged(self):
        response = self.client.post(
            "/api/papers/",
            {
                "title": "Novo",
                "abstract": "Um resumo científico com cinco palavras.",
                "owner": self.other.pk,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Paper.objects.get(pk=response.data["id"]).owner, self.user)

    def test_invalid_inputs_are_rejected(self):
        for changes in [
            {"title": " "},
            {"abstract": "curto"},
            {"abstract": "x " * 10001},
            {"language": "xx"},
        ]:
            with self.subTest(changes=list(changes)):
                payload = {
                    "title": "Estudo",
                    "abstract": "Um resumo com pelo menos cinco palavras.",
                    **changes,
                }
                self.assertEqual(self.client.post("/api/papers/", payload).status_code, 400)

    def test_update_and_delete(self):
        url = f"/api/papers/{self.paper.pk}/"
        response = self.client.patch(url, {"title": "Atualizado"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Atualizado")
        review_paper(self.paper)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Review.objects.filter(paper_id=self.paper.pk).exists())

    def test_review_is_persisted_and_idempotent(self):
        url = f"/api/papers/{self.paper.pk}/review/"
        first = self.client.post(url)
        second = self.client.post(url)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertIn("repeated_word", [item["code"] for item in first.data["findings"]])
        self.assertEqual(Review.objects.count(), 1)

    def test_editing_abstract_creates_new_review_and_keeps_history(self):
        url = f"/api/papers/{self.paper.pk}/"
        self.client.post(url + "review/")
        self.client.patch(url, {"abstract": "Este resumo foi modificado com novos resultados."})
        self.assertEqual(self.client.post(url + "review/").status_code, 201)
        self.assertEqual(self.client.get(url + "reviews/").data["count"], 2)

    def test_search_and_pagination(self):
        for index in range(11):
            Paper.objects.create(
                owner=self.user,
                title=f"Teste {index}",
                abstract="Resumo científico usado neste teste automatizado.",
            )
        response = self.client.get("/api/papers/?search=Teste&ordering=title")
        self.assertEqual(response.data["count"], 11)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(self.client.get("/api/papers/?search=Privado").data["count"], 0)

    def test_token_login_and_logout_revokes_access(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/auth/token/", {"username": "arthur", "password": "test-password-871"}
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(self.client.get("/api/papers/").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/papers/").status_code, 401)

    def test_bad_password_is_rejected_and_login_is_throttled(self):
        self.client.force_authenticate(None)
        for _ in range(10):
            self.assertEqual(
                self.client.post(
                    "/api/auth/token/", {"username": "arthur", "password": "incorrect"}
                ).status_code,
                400,
            )
        self.assertEqual(self.client.post("/api/auth/token/", {}).status_code, 429)

    def test_session_logout(self):
        self.client.force_authenticate(None)
        self.client.login(username="arthur", password="test-password-871")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/papers/").status_code, 401)

    def test_database_prevents_duplicate_review(self):
        review, _ = review_paper(self.paper)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(
                paper=self.paper, source_hash=review.source_hash, word_count=1, sentence_count=1
            )

    def test_home_is_public(self):
        self.client.force_authenticate(None)
        self.assertContains(self.client.get("/"), "PaperTrail")


class TextAnalysisTests(TestCase):
    def test_unicode_and_repeated_words(self):
        result = analyze_text("Ciência ciência contribui para a sociedade.")
        self.assertEqual(result["word_count"], 6)
        self.assertEqual(result["sentence_count"], 1)
        self.assertIn("repeated_word", [item["code"] for item in result["findings"]])

    def test_long_sentence(self):
        result = analyze_text(" ".join(f"palavra{i}" for i in range(60)) + ".")
        self.assertEqual([item["code"] for item in result["findings"]], ["long_sentence"])

    def test_no_findings(self):
        text = ". ".join(" ".join(f"palavra{i}" for i in range(20)) for _ in range(3))
        self.assertEqual(analyze_text(text)["findings"], [])

    def test_empty_text(self):
        result = analyze_text("")
        self.assertEqual(result["word_count"], 0)
        self.assertEqual(result["sentence_count"], 0)

    @patch("papers.management.commands.seed_demo.getpass", return_value="demo-test-password-492!")
    def test_seed_is_idempotent(self, prompt):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Paper.objects.count(), 2)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(get_user_model().objects.get().is_staff)
        prompt.assert_called_once()
