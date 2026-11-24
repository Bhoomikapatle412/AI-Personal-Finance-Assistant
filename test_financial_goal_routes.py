
import os
import unittest

# Use an isolated in-memory SQLite database.
os.environ["DATABASE_URL"] = "sqlite://"

from app import create_app
from extensions import db
from models import User
from models.financial_goal import FinancialGoal


class TestFinancialGoalRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False
        )

    def setUp(self):
        # Create a clean database for every test.
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            self.user = User(
                full_name="Test User",
                email="test@example.com",
                password_hash="test-password"
            )

            self.other_user = User(
                full_name="Other User",
                email="other@example.com",
                password_hash="test-password"
            )

            db.session.add_all([
                self.user,
                self.other_user
            ])
            db.session.commit()

            self.user_id = self.user.id
            self.other_user_id = self.other_user.id

            # Ensure the test users are genuinely different.
            self.assertNotEqual(
                self.user_id,
                self.other_user_id
            )

        # Create a client authenticated as the first user.
        self.client = self.app.test_client()
        self.login_as(self.client, self.user_id)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.session.remove()

    # --------------------------------------------------
    # AUTHENTICATION HELPER
    # --------------------------------------------------

    def login_as(self, client, user_id):
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    # --------------------------------------------------
    # GOAL CREATION HELPERS
    # --------------------------------------------------

    def create_goal(self):
        response = self.client.post(
            "/financial-goals/",
            json={
                "name": "Emergency Fund",
                "description": "Savings for emergencies",
                "target_amount": "50000",
                "target_date": "2027-12-31"
            }
        )

        self.assertEqual(response.status_code, 201)

        return response.get_json()["goal"]["id"]

    def create_goal_for_other_user(self):
        # Create the second user's goal directly in the database.
        # This avoids switching authentication sessions during
        # authorization tests.
        with self.app.app_context():
            goal = FinancialGoal(
                user_id=self.other_user_id,
                name="Private Goal",
                description="Another user's private savings goal",
                target_amount=20000,
                target_date=None
            )

            db.session.add(goal)
            db.session.commit()

            return goal.id

    # --------------------------------------------------
    # CREATE GOAL
    # --------------------------------------------------

    def test_create_goal(self):
        response = self.client.post(
            "/financial-goals/",
            json={
                "name": "Emergency Fund",
                "description": "Savings for emergencies",
                "target_amount": "50000",
                "target_date": "2027-12-31"
            }
        )

        self.assertEqual(response.status_code, 201)

        data = response.get_json()

        self.assertIn("goal", data)
        self.assertEqual(
            data["goal"]["name"],
            "Emergency Fund"
        )
        self.assertEqual(
            float(data["goal"]["target_amount"]),
            50000.0
        )

    def test_reject_invalid_goal_amount(self):
        response = self.client.post(
            "/financial-goals/",
            json={
                "name": "Invalid Goal",
                "target_amount": "0",
                "target_date": "2027-12-31"
            }
        )

        self.assertEqual(response.status_code, 400)

    # --------------------------------------------------
    # LIST AND RETRIEVE GOALS
    # --------------------------------------------------

    def test_list_goals(self):
        self.create_goal()

        response = self.client.get(
            "/financial-goals/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("goals", data)
        self.assertEqual(len(data["goals"]), 1)

    def test_get_goal(self):
        goal_id = self.create_goal()

        response = self.client.get(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("goal", data)
        self.assertEqual(
            data["goal"]["id"],
            goal_id
        )

    # --------------------------------------------------
    # CONTRIBUTIONS
    # --------------------------------------------------

    def test_add_contribution(self):
        goal_id = self.create_goal()

        response = self.client.post(
            f"/financial-goals/{goal_id}/contributions",
            json={
                "amount": "10000",
                "note": "First monthly saving"
            }
        )

        self.assertEqual(response.status_code, 201)

        data = response.get_json()

        self.assertIn("contribution", data)

        goal_response = self.client.get(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(
            goal_response.status_code,
            200
        )

        goal_data = goal_response.get_json()["goal"]

        self.assertEqual(
            float(goal_data["saved_amount"]),
            10000.0
        )

    def test_reject_excessive_contribution(self):
        goal_id = self.create_goal()

        response = self.client.post(
            f"/financial-goals/{goal_id}/contributions",
            json={
                "amount": "60000",
                "note": "Exceeds target"
            }
        )

        self.assertEqual(response.status_code, 400)

    # --------------------------------------------------
    # UPDATE GOAL
    # --------------------------------------------------

    def test_update_goal(self):
        goal_id = self.create_goal()

        response = self.client.put(
            f"/financial-goals/{goal_id}",
            json={
                "name": "Updated Emergency Fund",
                "target_amount": "75000"
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(
            data["goal"]["name"],
            "Updated Emergency Fund"
        )

        self.assertEqual(
            float(data["goal"]["target_amount"]),
            75000.0
        )

    def test_clear_target_date(self):
        goal_id = self.create_goal()

        response = self.client.put(
            f"/financial-goals/{goal_id}",
            json={
                "target_date": None
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIsNone(
            data["goal"]["target_date"]
        )

    # --------------------------------------------------
    # DELETE GOAL
    # --------------------------------------------------

    def test_delete_goal(self):
        goal_id = self.create_goal()

        response = self.client.delete(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(response.status_code, 200)

        get_response = self.client.get(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(
            get_response.status_code,
            404
        )

    # --------------------------------------------------
    # USER OWNERSHIP AND AUTHORIZATION
    # --------------------------------------------------

    def test_user_cannot_access_another_users_goal(self):
        # Create a goal owned by the second user.
        goal_id = self.create_goal_for_other_user()

        # First user attempts to access it.
        response = self.client.get(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(response.status_code, 404)

        # Verify the goal still exists and belongs to its owner.
        with self.app.app_context():
            goal = db.session.get(
                FinancialGoal,
                goal_id
            )

            self.assertIsNotNone(goal)
            self.assertEqual(
                goal.user_id,
                self.other_user_id
            )

    def test_user_cannot_delete_another_users_goal(self):
        # Create a goal owned by the second user.
        goal_id = self.create_goal_for_other_user()

        # First user attempts to delete it.
        response = self.client.delete(
            f"/financial-goals/{goal_id}"
        )

        self.assertEqual(response.status_code, 404)

        # Verify that the goal was not deleted.
        with self.app.app_context():
            goal = db.session.get(
                FinancialGoal,
                goal_id
            )

            self.assertIsNotNone(goal)
            self.assertEqual(
                goal.user_id,
                self.other_user_id
            )


if __name__ == "__main__":
    unittest.main()
