import unittest
from copy import deepcopy
from unittest.mock import patch

from experiments.sentiment_batching import controls, experiment
from experiments.sentiment_batching.score import compare, value
from thesis.research import sentiment


class BatchingTests(unittest.TestCase):
    def test_partition_preserves_sources_and_parents_exactly(self):
        packet = controls.packet()
        original = deepcopy(packet)
        parts = experiment.batches(packet, 4)
        self.assertEqual([s for p in parts for s in p['sources']], packet['sources'])
        self.assertEqual(packet, original)
        self.assertEqual(parts[1]['sources'][1]['conversation'], packet['sources'][5]['conversation'])

    def test_all_news_remain_available_across_boundary(self):
        packet = controls.packet()
        for part in experiment.batches(packet, 4):
            news = {s['id'] for s in part['sources'] + part['comparison_sources'] if s['channel'] == 'news'}
            self.assertEqual(news, {s['id'] for s in packet['sources'] if s['channel'] == 'news'})
            self.assertFalse({s['id'] for s in part['sources']} & {s['id'] for s in part['comparison_sources']})

    def test_full_request_is_unchanged(self):
        packet = controls.packet()
        self.assertEqual(sentiment.request_for(packet), sentiment.request_for(experiment.batches(packet, 16)[0]))

    def test_profiles_and_instructions_are_unchanged(self):
        packet = controls.packet()
        full = sentiment.request_for(packet)
        for part in experiment.batches(packet, 4):
            body = sentiment.request_for(part)
            for k in ('model','max_output_tokens','reasoning','store','service_tier'):
                self.assertEqual(body[k], full[k])
            self.assertEqual(body['input'][0],full['input'][0])
            experiment.ledger.estimate(body)

    def test_invalid_size_and_duplicate_sources_rejected(self):
        packet = controls.packet()
        for n in (0,-1,1.5):
            with self.assertRaises(ValueError):experiment.batches(packet,n)
        packet['sources'].append(packet['sources'][0])
        with self.assertRaises(ValueError):experiment.batches(packet,4)

    def test_missing_and_duplicate_batches_never_form_complete_output(self):
        packet=controls.packet()
        parts=experiment.batches(packet,4)
        for subset in (parts[:-1],parts+[parts[0]]):
            with self.assertRaises(ValueError):experiment.combine(packet,subset,[{}]*len(subset))

    def test_incomplete_result_never_parsed_as_complete(self):
        with self.assertRaises(ValueError):
            experiment.raw_result({'response_body':{'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}}})

    def test_global_validation_after_batch_validation(self):
        packet=controls.packet()
        parts=experiment.batches(packet,4)
        # Even if per-batch validation succeeds, combined relations must be
        # checked against all labels. A failure cannot publish a partial total.
        with patch.object(sentiment,'render',side_effect=[{}, {}, {}, ValueError('Unrelated reference')]) as render:
            with patch.object(experiment,'raw_result',return_value={'items':[],'coverage_links':[]}):
                with self.assertRaisesRegex(ValueError,'Unrelated reference'):
                    experiment.combine(packet,parts,[{}, {}, {}])
        self.assertEqual(render.call_count,4)

    def test_comparison_distinguishes_labels_from_summary(self):
        a={'items':[{'id':'a','sentiment':'positive','relevance':'relevant','basis':'expressed_evaluation','statement':'opinion'}],
           'coverage_links':[],'summary':{'social':{'tone':'thin sample'}}}
        b=deepcopy(a);b['items'][0]['sentiment']='negative'
        result=compare(a,b)
        self.assertEqual(result['tone_matches'],0)
        self.assertTrue(result['summary_equal'])
        self.assertEqual(result['changed']['a']['sentiment'],['positive','negative'])

    def test_comparison_rejects_missing_source(self):
        with self.assertRaises(ValueError):compare({'items':[{'id':'a'}]},{'items':[]})

    def test_coverage_comparison_is_order_independent(self):
        links=[{'source_id':'a','reference_source_id':'p','relation':'repeats'},
               {'source_id':'b','reference_source_id':'p','relation':'adds_detail'}]
        a={'items':[],'summary':{},'coverage_links':links}
        b=deepcopy(a);b['coverage_links'].reverse()
        self.assertTrue(compare(a,b)['coverage_equal'])

    def test_field_scoring_uses_separate_event_impact(self):
        item={'sentiment':'negative','reporting_basis':{'impact':'not_stated'},'context_passages':['p1']}
        self.assertEqual(value(item,'reporting.impact'),'not_stated')
        self.assertTrue(value(item,'context_passages_nonempty'))


if __name__=='__main__':unittest.main()
