import unittest

import api


class ApiConsistencyTests(unittest.TestCase):
    def test_dashboard_and_failure_stats_use_same_config_totals(self):
        client = api.app.test_client()
        overview = client.get('/api/dashboard/overview')
        stats = client.get('/api/failures/stats')

        self.assertEqual(overview.status_code, 200)
        self.assertEqual(stats.status_code, 200)

        overview_json = overview.get_json() or {}
        stats_json = stats.get_json() or {}
        self.assertEqual(
            overview_json.get('failures', {}).get('by_config', {}),
            stats_json.get('by_config', {}),
        )


if __name__ == '__main__':
    unittest.main()
