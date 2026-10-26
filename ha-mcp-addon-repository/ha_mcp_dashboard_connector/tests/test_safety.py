import unittest
from src.safety import ProposalStore

class ProposalStoreTests(unittest.TestCase):
    def test_requires_exact_target_and_diff(self):
        store = ProposalStore(60)
        p = store.create("dashboard:test", "- title: Old\n+ title: New", now=100)
        self.assertFalse(store.confirm(p.proposal_id, "dashboard:other", p.diff, now=101))
        self.assertFalse(store.confirm(p.proposal_id, p.target, "different diff", now=101))
        self.assertTrue(store.confirm(p.proposal_id, p.target, p.diff, now=101))

    def test_confirmation_is_one_use(self):
        store = ProposalStore(60)
        p = store.create("dashboard:test", "diff", now=100)
        self.assertTrue(store.confirm(p.proposal_id, p.target, p.diff, now=101))
        self.assertFalse(store.confirm(p.proposal_id, p.target, p.diff, now=102))
        self.assertTrue(store.consume_confirmation(p.proposal_id, p.target, p.diff))
        self.assertFalse(store.consume_confirmation(p.proposal_id, p.target, p.diff))

    def test_expired_proposal_rejected(self):
        store = ProposalStore(5)
        p = store.create("dashboard:test", "diff", now=100)
        self.assertFalse(store.confirm(p.proposal_id, p.target, p.diff, now=106))

    def test_empty_proposal_rejected(self):
        store = ProposalStore()
        with self.assertRaises(ValueError):
            store.create("", "diff")

if __name__ == "__main__":
    unittest.main()
