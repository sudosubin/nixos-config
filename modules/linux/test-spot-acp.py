"""ACP contract tests, without models, agents, AWS calls or private transcripts."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('acp',Path(__file__).with_name('spot_acp.py'))
acp=importlib.util.module_from_spec(spec);spec.loader.exec_module(acp)


def request(ident,method='session/prompt',params=None):
    return {'jsonrpc':'2.0','id':ident,'method':method,'params':params or {}}


def response(ident,result):
    return {'jsonrpc':'2.0','id':ident,'result':result}


class ACPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.protocol=acp.work.Protocol(Path(self.temp.name)/'runtime',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='test')
        self.protocol.initialize();self.snapshots=[];self.t=acp.Tracker(self.protocol,lambda state:self.snapshots.append(dict(state)))
        self.patch=patch.object(acp.work,'process_start',return_value=123);self.patch.start();self.addCleanup(self.patch.stop)

    def initialize(self):
        self.assertTrue(self.t.client(request(0,'initialize'))[0])
        self.t.backend(response(0,{'protocolVersion':1,'agentCapabilities':{}}))
        self.assertTrue(self.t.initialized);self.assertEqual(self.protocol.blockers(),[])

    def test_initialization_is_required(self):
        forward,error=self.t.client(request(1));self.assertFalse(forward);self.assertEqual(error['error']['code'],-32074)
        self.assertEqual(self.t.pending,{})

    def test_prompt_is_leased_before_forward(self):
        self.initialize();forward,error=self.t.client(request(1))
        self.assertTrue(forward);self.assertIsNone(error);self.assertTrue(self.protocol.blockers())

    def test_fence_rejects_new_prompt_without_forward_or_lease(self):
        self.initialize();self.protocol.seal()
        forward,error=self.t.client(request(1));self.assertFalse(forward)
        self.assertEqual(error['id'],1);self.assertEqual(error['error']['code'],-32074)
        self.assertEqual(self.t.state()['admission_rejections'],1)
        self.assertEqual(self.protocol.blockers(),[])

    def test_existing_request_blocks_commit_then_completes_behind_fence(self):
        self.initialize();self.t.client(request(1));self.protocol.seal()
        with self.assertRaises(RuntimeError):
            with self.protocol.commit():self.fail('must not release active model turn')
        self.t.backend(response(1,{'stopReason':'end_turn'}))
        self.assertEqual(self.protocol.blockers(),[])

    def test_all_known_terminal_reasons_complete(self):
        self.initialize()
        for index,reason in enumerate(sorted(acp.STOP_REASONS),1):
            with self.subTest(reason=reason):
                self.t.client(request(index));self.t.backend(response(index,{'stopReason':reason}))
                self.assertEqual(self.protocol.blockers(),[])

    def test_ack_is_not_completion(self):
        self.initialize();self.t.client(request(1));self.t.backend(response(1,{}))
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_unknown_stop_reason_not_idle(self):
        self.initialize();self.t.client(request(1));self.t.backend(response(1,{'stopReason':'still_running'}))
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_cancel_does_not_release_prompt_lease(self):
        self.initialize();self.t.client(request(1));self.protocol.seal()
        self.assertEqual(self.t.client({'jsonrpc':'2.0','method':'session/cancel','params':{'sessionId':'private'}}),(True,None))
        self.assertTrue(self.protocol.blockers())
        self.t.backend(response(1,{'stopReason':'cancelled'}));self.assertEqual(self.protocol.blockers(),[])

    def test_async_extension_ack_not_misclassified_as_idle(self):
        self.initialize();self.t.client(request(1,'message/send'));self.t.backend(response(1,{'accepted':True}))
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_non_string_stop_reason_is_unknown_not_reader_crash(self):
        self.initialize();self.t.client(request(1));self.t.backend(response(1,{'stopReason':[]}))
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_unknown_notification_is_not_silently_classified_as_idle(self):
        self.initialize();self.t.backend({'jsonrpc':'2.0','method':'vendor/async_work','params':{}})
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_malformed_update_type_is_unknown_not_reader_crash(self):
        self.initialize();self.t.backend({'jsonrpc':'2.0','method':'session/update','params':{'update':{'sessionUpdate':[]}}})
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_output_eof_fences_new_requests_even_before_process_exit(self):
        self.initialize();self.t.transport_closed()
        self.assertFalse(self.t.state()['healthy']);self.assertFalse(self.t.client(request(1))[0])
        self.assertTrue(self.t.backend_exit(0))

    def test_nonzero_idle_backend_exit_remains_unknown(self):
        self.initialize();self.assertFalse(self.t.backend_exit(1));self.assertTrue(self.protocol.blockers())

    def test_request_scoped_control_completes(self):
        self.initialize()
        for index,method in enumerate(['session/list','_kiro.dev/session/list','_kiro.dev/settings/list'],1):
            with self.subTest(method=method):
                self.t.client(request(index,method));self.t.backend(response(index,{'sessions':[]}))
                self.assertTrue(self.t.healthy);self.assertEqual(self.protocol.blockers(),[])

    def test_backend_error_stays_unknown(self):
        self.initialize();self.t.client(request(1));self.t.backend({'jsonrpc':'2.0','id':1,'error':{'code':-1,'message':'not logged or failure'}})
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers());self.assertFalse(self.t.backend_exit())

    def test_correlation_distinguishes_integer_and_string_ids(self):
        self.initialize();self.t.client(request(1));self.t.client(request('1'))
        self.assertEqual(len(self.t.pending),2)
        self.t.backend(response(1,{'stopReason':'end_turn'}));self.assertEqual(len(self.t.pending),1)
        self.t.backend(response('1',{'stopReason':'end_turn'}));self.assertEqual(self.protocol.blockers(),[])

    def test_duplicate_id_not_forwarded(self):
        self.initialize();self.t.client(request(1));forward,error=self.t.client(request(1))
        self.assertFalse(forward);self.assertEqual(error['error']['code'],-32600);self.assertFalse(self.t.healthy)

    def test_bad_ids_fail_closed(self):
        self.initialize()
        for ident in [True,None,{},[],1.5,'x'*257]:
            with self.subTest(ident=ident):self.assertFalse(self.t.client(request(ident))[0])
        self.assertFalse(self.t.healthy)

    def test_unknown_notification_cannot_initiate_work(self):
        self.initialize();forward,error=self.t.client({'jsonrpc':'2.0','method':'session/prompt','params':{'text':'secret'}})
        self.assertFalse(forward);self.assertFalse(self.t.healthy)

    def test_bad_client_envelopes_never_forwarded(self):
        for data in [None,[],True,{}, {'jsonrpc':'1.0','id':1,'method':'initialize'}]:
            with self.subTest(data=data):self.assertFalse(self.t.client(data)[0])

    def test_backend_response_write_custody_kept_until_delivered(self):
        self.initialize();self.t.client(request(1))
        self.t.backend(response(1,{'stopReason':'end_turn'}),delivered=False)
        self.assertTrue(self.protocol.blockers())
        self.t.client_output_delivered()  # unrelated input delivery cannot clear output custody
        self.assertTrue(self.protocol.blockers())
        self.t.backend_output_delivered();self.assertEqual(self.protocol.blockers(),[])

    def test_tool_permission_response_custody_keeps_parent_turn_leased(self):
        self.initialize();self.t.client(request(1))
        self.t.backend(request(1,'session/request_permission'))
        self.t.backend(response(1,{'stopReason':'end_turn'}))
        self.assertTrue(self.protocol.blockers())
        self.assertTrue(self.t.client(response(1,{'allowed':False}),delivered=False)[0])
        self.t.backend_output_delivered();self.assertTrue(self.protocol.blockers())
        self.t.client_output_delivered();self.assertEqual(self.protocol.blockers(),[])

    def test_unsolicited_tool_request_not_idle(self):
        self.initialize();self.t.backend(request(1,'fs/write_text_file'))
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_work_notification_without_request_stays_unknown(self):
        self.initialize();self.t.backend({'jsonrpc':'2.0','method':'session/update','params':{'update':{'sessionUpdate':'tool_call'}}})
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_streaming_updates_never_complete_turn(self):
        self.initialize();self.t.client(request(1))
        self.t.backend({'jsonrpc':'2.0','method':'session/update','params':{'update':{'sessionUpdate':'agent_message_chunk','content':{'text':'secret'}}}})
        self.assertTrue(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_idle_metadata_notification_allowed(self):
        self.initialize();self.t.backend({'jsonrpc':'2.0','method':'session/update','params':{'update':{'sessionUpdate':'current_mode_update'}}})
        self.assertTrue(self.t.healthy);self.assertEqual(self.protocol.blockers(),[])

    def test_unknown_response_cannot_clear_another_lease(self):
        self.initialize();self.t.client(request(1));self.t.backend(response(999,{'stopReason':'end_turn'}))
        self.assertFalse(self.t.healthy);self.assertTrue(self.t.pending);self.assertTrue(self.protocol.blockers())

    def test_eof_or_backend_exit_with_pending_work_not_idle(self):
        self.initialize();self.t.client(request(1));self.assertFalse(self.t.backend_exit())
        self.assertTrue(self.protocol.blockers())

    def test_clean_idle_exit_can_remove_participant(self):
        self.initialize();self.assertTrue(self.t.backend_exit())

    def test_heartbeat_never_marks_work_complete(self):
        self.initialize();self.t.client(request(1));self.t.heartbeat()
        self.assertTrue(self.protocol.blockers())

    def test_private_payload_and_rpc_ids_never_persisted(self):
        self.initialize();self.t.client(request('SECRET_RPC_ID',params={'sessionId':'SECRET_SESSION','content':[{'text':'SECRET_PROMPT'}]}))
        data=''.join(p.read_text() for p in self.protocol.leases.iterdir())+json.dumps(self.snapshots)
        for secret in ['SECRET_RPC_ID','SECRET_SESSION','SECRET_PROMPT']:self.assertNotIn(secret,data)

    def test_unverified_participant_never_grants_idle_authority(self):
        p=self.protocol.runtime/'participants'/'acp-fixture';p.write_text('{}')
        self.assertEqual(self.protocol.blockers()[0]['reason'],'participant_unverified')

    def test_real_native_empty_inventory_and_metrics_preserve_request_custody(self):
        self.initialize();self.t.client(request(1))
        frames=[('_kiro.dev/subagent/list_update',{'subagents':[],'pendingStages':[]}),
                ('_kiro.dev/mcp/governance_disabled',{'sessionId':'fixture','apiFailure':True}),
                ('_kiro.dev/webTools/governance_disabled',{'sessionId':'fixture','apiFailure':False}),
                ('_kiro.dev/commands/available',{'sessionId':'fixture','commands':[{'name':'help','description':'declaration','meta':{}}],'prompts':[],'tools':[],'mcpServers':[]}),
                ('_kiro.dev/metadata',{'sessionId':'fixture','contextUsagePercentage':0.0}),
                ('_kiro.dev/metadata',{'sessionId':'fixture','turnDurationMs':5})]
        for method,params in frames:
            self.t.backend({'jsonrpc':'2.0','method':method,'params':params})
            self.assertTrue(self.t.healthy);self.assertTrue(self.protocol.blockers())
        self.t.backend(response(1,{'stopReason':'end_turn'}));self.assertEqual(self.protocol.blockers(),[])

    def test_nonempty_or_pending_subagents_never_become_idle(self):
        for params in [{'subagents':[{}],'pendingStages':[]},{'subagents':[],'pendingStages':[{}]},
                       {'subagents':[],'pendingStages':[],'unknown':True}]:
            with self.subTest(params=params):self.assertFalse(acp.kiro_metadata('_kiro.dev/subagent/list_update',params))
        self.initialize();self.t.backend({'jsonrpc':'2.0','method':'_kiro.dev/subagent/list_update','params':{'subagents':[{}],'pendingStages':[]}})
        self.t.backend({'jsonrpc':'2.0','method':'_kiro.dev/subagent/list_update','params':{'subagents':[],'pendingStages':[]}})
        self.assertFalse(self.t.healthy);self.assertTrue(self.protocol.blockers())

    def test_tool_mcp_and_prompt_inventories_require_separate_tracking(self):
        baseline={'sessionId':'fixture','commands':[],'prompts':[],'tools':[],'mcpServers':[]}
        for key in ['prompts','tools','mcpServers']:
            with self.subTest(key=key):self.assertFalse(acp.kiro_metadata('_kiro.dev/commands/available',{**baseline,key:[{}]}))
        for commands in [[{}],[{'name':'help','description':'declaration','work':True}],{}]:
            self.assertFalse(acp.kiro_metadata('_kiro.dev/commands/available',{**baseline,'commands':commands}))

    def test_malformed_or_new_native_metrics_fail_closed(self):
        for params in [None,{}, {'sessionId':'fixture'}, {'sessionId':'fixture','active':False},
                       {'sessionId':'fixture','turnDurationMs':True}, {'sessionId':'fixture','turnDurationMs':-1},
                       {'sessionId':'fixture','contextUsagePercentage':float('nan')},
                       {'sessionId':'fixture','contextUsagePercentage':float('inf')},
                       {'sessionId':'fixture','contextUsagePercentage':101},
                       {'sessionId':'fixture','contextUsagePercentage':10**1000}]:
            with self.subTest(params=params):self.assertFalse(acp.kiro_metadata('_kiro.dev/metadata',params))
        self.assertFalse(acp.kiro_metadata('_kiro.dev/mcp/governance_disabled',{'sessionId':'fixture','apiFailure':1}))
        self.assertFalse(acp.kiro_metadata('_kiro.dev/mcp/governance_disabled',{'sessionId':'fixture','apiFailure':False,'work':True}))

    def test_closed_admission_prevents_backend_spawn(self):
        self.protocol.seal()
        with patch.object(acp.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'admission closed'):
                acp.bridge(self.protocol,['PRIVATE_STARTUP_ARGUMENT'])
        spawn.assert_not_called()
        self.assertEqual(self.protocol.blockers(),[])
        self.assertEqual(list((self.protocol.runtime/'participants').iterdir()),[])

    def test_startup_lease_precedes_spawn_and_uncertain_spawn_stays_blocked(self):
        def spawn(*args,**kwargs):
            self.assertEqual([b['reason'] for b in self.protocol.blockers()],['running_job'])
            raise OSError('fixture spawn outcome uncertain')
        with patch.object(acp.subprocess,'Popen',side_effect=spawn):
            with self.assertRaises(OSError):acp.bridge(self.protocol,['PRIVATE_STARTUP_ARGUMENT'])
        self.assertEqual([b['reason'] for b in self.protocol.blockers()],['running_job'])
        data=''.join(p.read_text() for p in self.protocol.leases.iterdir())
        self.assertNotIn('PRIVATE_STARTUP_ARGUMENT',data)
        self.assertNotIn('fixture spawn outcome',data)

    def test_failed_participant_publication_keeps_startup_custody_without_killing_backend(self):
        child=Mock(pid=os.getpid())
        with patch.object(acp.subprocess,'Popen',return_value=child), \
                patch.object(acp.Participant,'publish',side_effect=OSError('fixture publication failure')):
            with self.assertRaises(OSError):acp.bridge(self.protocol,['not-executed'])
        self.assertEqual([b['reason'] for b in self.protocol.blockers()],['running_job'])
        child.terminate.assert_not_called();child.kill.assert_not_called();child.wait.assert_not_called()

    def test_startup_handoff_overlaps_uninitialized_unverified_participant(self):
        def after_handoff():
            self.assertEqual([b['reason'] for b in self.protocol.blockers()],['participant_unverified'])
            records=[json.loads(p.read_text()) for p in (self.protocol.runtime/'participants').iterdir()]
            self.assertEqual(len(records),1);self.assertFalse(records[0]['initialized'])
            self.assertEqual(records[0]['reason'],'initializing')
            raise RuntimeError('fixture stops before threads')
        with patch.object(acp.subprocess,'Popen',return_value=Mock(pid=os.getpid())), \
                patch.object(acp.threading,'Lock',side_effect=after_handoff):
            with self.assertRaisesRegex(RuntimeError,'fixture stops before threads'):
                acp.bridge(self.protocol,['not-executed'])
        self.assertEqual(list(self.protocol.leases.iterdir()),[])
        self.assertEqual([b['reason'] for b in self.protocol.blockers()],['participant_unverified'])

    def test_actual_native_extension_names_and_acks_are_not_request_scoped(self):
        self.initialize()
        for index,(method,result) in enumerate([('_message/send',{'ok':True}),
                                               ('_session/steer',{'queued':True}),
                                               ('_session/steer/clear',{})],1):
            with self.subTest(method=method):
                self.assertNotIn(method,acp.REQUEST_SCOPED)
                tracker=acp.Tracker(self.protocol);tracker.initialized=True
                self.assertTrue(tracker.client(request(index,method))[0])
                tracker.backend(response(index,result))
                self.assertFalse(tracker.healthy);self.assertTrue(tracker.pending)
        self.assertTrue(self.protocol.blockers())

    def test_read_frame_rejects_truncation_and_oversize(self):
        for data in [b'{}',b'x'*(acp.MAX_FRAME+1)]:
            with self.subTest(size=len(data)),self.assertRaises(ValueError):acp.read_frame(io.BytesIO(data))
        self.assertEqual(acp.read_frame(io.BytesIO(b'{}\n')),b'{}\n')
        self.assertIsNone(acp.read_frame(io.BytesIO()))


if __name__=='__main__':unittest.main()
