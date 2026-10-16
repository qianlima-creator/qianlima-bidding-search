"""Known district-granularity limits must stop silent scope widening."""
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import area_resolver as a
import qianlima_skill as r
from complex_query_plan import preflight_complex_plan


class AreaGranularityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {'QIANLIMA_SKILL_STATE_DIR':tmp.name})
        env.start()
        self.addCleanup(env.stop)

    sources = [('project', 'search', 'normalize_project_search_query'),
               ('purchase_intention', 'search-purchase', 'normalize_purchase_search_query'),
               ('expiring_project', 'search-expiring', 'normalize_expiring_search_query')]

    def query(self, source, ids):
        q = {'areaIds': ids, 'numPerPage': 5, 'currentPage': 1}
        q.update({'keywordGroups': [{'keywords': ['设备'], 'matchScopes': [2, 9]}]} if source == 'project' else {'keywords': ['设备']})
        return q

    def test_known_district_is_identified_but_not_executable(self):
        for name, parent, whole in [('海淀', None, '北京市'), ('上海浦东', None, '上海市'),
                                    ('河西区', '天津', '天津市'), ('城口县', '重庆', '重庆市'),
                                    ('北京（海淀区）', None, '北京市')]:
            with self.subTest(name=name):
                p = a.resolve(name, parent=parent)
                self.assertEqual(p['resolution_status'], 'unsupported', p)
                self.assertNotIn('effective_query', p)
                self.assertIn('是否', p['user_message'])
                self.assertIn(whole, p['user_message'])

    def test_all_86_catalog_districts_are_blocked_without_deleting_ids(self):
        c = a.catalog()
        ids = [i for i,chain in c.chains.items() if chain[0] in a.MUNICIPALITIES
               and len(chain) >= 3 and i not in c.upper_choices]
        self.assertEqual(len(ids), 86)
        self.assertEqual(c.validate_ids(ids), ids)
        for i in ids:
            self.assertEqual(c.resolve(c.by_id[i]['name'])['resolution_status'], 'unsupported')

    def test_whole_regions_and_other_districts_remain_executable(self):
        for name, ids in [('北京', [2]), ('上海', [24]), ('天津', [26]), ('重庆', [31]),
                          ('香港', [3557]), ('澳门', [3558]), ('台湾', [3559]),
                          ('深圳南山', [2807]), ('长春朝阳区', [3181]), ('简阳', [2251,3500])]:
            self.assertEqual(a.resolve(name)['effective_query']['areaIds'], ids)

    def test_ambiguity_resolved_before_capability_decision(self):
        self.assertEqual(a.resolve('朝阳区')['resolution_status'], 'ambiguous')
        self.assertEqual(a.resolve('朝阳区', parent='北京')['resolution_status'], 'unsupported')
        self.assertEqual(a.resolve('朝阳区', parent='长春')['effective_query']['areaIds'], [3181])

    def test_mixed_request_does_not_execute_partial_scope(self):
        p = a.resolve('深圳南山区、北京海淀区')
        self.assertEqual(p['resolution_status'], 'unsupported')
        self.assertNotIn('effective_query', p)
        self.assertIn('北京市', p['user_message'])
        self.assertIn('区县', p['user_message'])
        self.assertEqual(p['unresolved_parts'], ['北京海淀区'])

    def test_unmapped_special_region_qualifiers_preserved(self):
        for name, parent in [('香港（九龙）', None), ('九龙', '香港'),
                             ('澳门氹仔', None), ('台湾台北中正区', None)]:
            p = a.resolve(name, parent=parent)
            self.assertNotIn('effective_query', p)
            self.assertIn(name, p['user_message'])
            self.assertIn('暂不支持区县', p['user_message'])

    def test_three_searches_reject_direct_district_ids_before_client_creation(self):
        for source, command, _ in self.sources:
            args = r.build_parser().parse_args([command, '--query-json', json.dumps(self.query(source, [3320]))])
            with self.subTest(source=source), patch.object(r, 'build_client', side_effect=AssertionError('受限查询不应创建API客户端')) as client:
                p = args.func(args)
                self.assertFalse(p['ok'])
                self.assertEqual(p['error_code'], 'AREA_SCOPE_UNSUPPORTED')
                client.assert_not_called()

    def test_low_level_guard_rejects_districts_for_all_three_sources(self):
        for source, _, _ in self.sources:
            path = {'project':'/api/search', 'purchase_intention':'/api/search/purchase', 'expiring_project':'/api/search/expiring'}[source]
            with self.subTest(source=source):
                with self.assertRaises(r.SkillError) as e:
                    r.validate_endpoint_request('POST', path, self.query(source, [3320]))
                self.assertEqual(e.exception.code, 'AREA_SCOPE_UNSUPPORTED')

    def test_complex_preflight_has_no_executable_operations(self):
        for source, _, _ in self.sources:
            plan = {'conditions': [{'id':'k','type':'keyword','value':'设备'}, {'id':'a','type':'area','value':[3320]}],
                    'operations':[{'id':'s','action':'search','data_source':source}]}
            p = preflight_complex_plan(plan, r.normalize_complex_operation)
            self.assertFalse(p['ok'])
            self.assertEqual(p['approved_operations'], [])

    def test_old_district_sessions_cannot_page_or_refine_without_fixing_scope(self):
        for source, _, _ in self.sources:
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'QIANLIMA_SKILL_STATE_DIR':tmp}):
                snap = r.save_search_snapshot(session_id=str(uuid.uuid4()),result_type=source,
                       effective_query=self.query(source,[3320]),viewed_cards=[],total_count=20,page_count=4)
                ctx = ['--session-id',snap['session_id'],'--result-set-id',snap['result_set_id']]
                for command in [['next',*ctx], ['refine',*ctx,'--query-json','{"excludeWords":["维修"]}']]:
                    args = r.build_parser().parse_args(command)
                    with patch.object(r,'build_client', side_effect=AssertionError('受限旧会话不应创建API客户端')) as client:
                        try:p = args.func(args)
                        except r.SkillError as e:self.assertEqual(e.code,'AREA_SCOPE_UNSUPPORTED')
                        else:self.assertEqual(p['error_code'],'AREA_SCOPE_UNSUPPORTED')
                        client.assert_not_called()

    def test_accepted_whole_scope_keeps_other_conditions_and_displays_true_scope(self):
        for source, command, normalize_name in self.sources:
            q = dict(self.query(source,[2]),excludeWords=['维修'])
            normalized,_ = getattr(r,normalize_name)(q)
            self.assertEqual(normalized['areaIds'],[2])
            self.assertEqual(normalized['excludeWords'],['维修'])
            self.assertIn('北京市', '\n'.join(r.user_query_lines(normalized)))
            self.assertNotIn('海淀', '\n'.join(r.user_query_lines(normalized)))

    def test_old_session_can_refine_to_accepted_whole_scope_then_page(self):
        for source, _, _ in self.sources:
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'QIANLIMA_SKILL_STATE_DIR':tmp}):
                original = dict(self.query(source,[3320]), excludeWords=['维修'])
                snap = r.save_search_snapshot(session_id=str(uuid.uuid4()),result_type=source,
                       effective_query=original,viewed_cards=[],total_count=20,page_count=4)
                ctx = ['--session-id',snap['session_id'],'--result-set-id',snap['result_set_id']]
                calls=[]
                def request(client, method, path, query=None):
                    r.validate_endpoint_request(method,path,query)
                    calls.append(dict(query))
                    client.last_request_path, client.last_request_query = path,dict(query)
                    return {'rowCount':20,'pageCount':4,'list':[]}
                args=r.build_parser().parse_args(['refine',*ctx,'--query-json','{"areaIds":[2]}'])
                with patch.object(r.ApiClient,'_request',request):
                    result=args.func(args)
                    self.assertTrue(result['ok'],result)
                    self.assertEqual(calls[0]['areaIds'],[2])
                    self.assertEqual(calls[0]['excludeWords'],['维修'])
                    self.assertNotIn('海淀', result['user_message'].split('\n\n')[0])
                    self.assertIn('北京市', result['user_message'].split('\n\n')[0])
                    follow=result['follow_up']
                    args=r.build_parser().parse_args(['next','--session-id',follow['session_id'],
                                                    '--result-set-id',follow['result_set_id']])
                    self.assertTrue(args.func(args)['ok'])
                self.assertEqual(calls[1]['areaIds'],[2])
                self.assertEqual(calls[1]['currentPage'],2)

if __name__ == '__main__':unittest.main()
