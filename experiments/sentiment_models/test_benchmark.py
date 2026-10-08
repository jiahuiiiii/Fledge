"""Standard-library-only checks for evaluation denominator/input correctness."""
import unittest
from benchmark import chunks, encode_chunk, metrics, normalized_labels, scoring_group, source_text, vader_label, weighted_scores


class BenchmarkTests(unittest.TestCase):
    def test_class_order_comes_from_config(self):
        self.assertEqual(normalized_labels({0: 'Neutral', 1: 'Positive', 2: 'Negative'}), ['neutral', 'positive', 'negative'])
        with self.assertRaises(ValueError):
            normalized_labels({0: 'LABEL_0', 1: 'LABEL_1', 2: 'LABEL_2'})

    def test_unclear_and_mixed_are_not_coerced(self):
        self.assertEqual(scoring_group(['neutral', 'unclear']), 'outside_three_way_contract')
        self.assertEqual(scoring_group(['mixed']), 'outside_three_way_contract')
        self.assertEqual(scoring_group(['positive', 'neutral']), 'multiple_acceptable_three_way')
        self.assertEqual(scoring_group([]), 'unlabelled')

    def test_unknown_prediction_is_a_miss(self):
        m = metrics([('positive', 'positive'), ('neutral', 'unclear'), ('negative', 'negative')])
        self.assertEqual((m['n'], m['correct']), (3, 2))
        self.assertEqual(m['confusion']['neutral']['other'], 1)

    def test_no_lost_or_repeated_chunk_tokens(self):
        original = list(range(1021))
        split = chunks(original, 510)
        self.assertEqual([len(x) for x in split], [510, 510, 1])
        self.assertEqual(sum(split, []), original)

    def test_length_weighted_scores(self):
        scores = weighted_scores([{'negative': 1., 'neutral': 0., 'positive': 0.}, {'negative': 0., 'neutral': 0., 'positive': 1.}], [3, 1])
        self.assertEqual(scores['negative'], .75)
        self.assertEqual(scores['positive'], .25)

    def test_hn_parent_and_generic_title_are_not_author_votes(self):
        source = {'platform': 'hackernews', 'title': 'Thread', 'text': 'Ignored duplicate', 'conversation': {'text': 'Parent'}, 'passages': [{'id': 'p0', 'quote': 'Thread'}, {'id': 'p1', 'quote': 'Child'}]}
        self.assertEqual(source_text(source), 'Child')
        source['platform'] = 'reddit'
        self.assertEqual(source_text(source), 'Thread\nChild')

    def test_vader_standard_boundary(self):
        self.assertEqual([vader_label(n) for n in [-.05, -.049, .049, .05]], ['negative', 'neutral', 'neutral', 'positive'])

    def test_chunk_encoding_has_exact_boundary_and_segment_ids(self):
        class Bert:
            cls_token_id = 101
            sep_token_id = 102
            model_input_names = ['input_ids', 'attention_mask', 'token_type_ids']
        value = encode_chunk(Bert(), [12, 34])
        self.assertEqual(value, {'input_ids': [101, 12, 34, 102], 'attention_mask': [1, 1, 1, 1], 'token_type_ids': [0, 0, 0, 0]})
        self.assertEqual(len(encode_chunk(Bert(), list(range(510)))['input_ids']), 512)


if __name__ == '__main__':
    unittest.main()
