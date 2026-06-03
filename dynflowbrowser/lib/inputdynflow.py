import os
import sys

import pandas as pd

from dynflowbrowser.lib.util import Util


class InputDynflow:

    def __init__(self, conf):
        self.conf = conf
        self.util = Util()
        self.get_dynflow_schema()

    def read_dynflow(self, dtype):
        inputfile = (self.conf.args.sosreport_path
                     + self.conf.dynflowdata[dtype]['inputfile'])
        if os.path.islink(inputfile):
            self.util.debug(
                "W",
                f"read_dynflow: {self.conf.dynflowdata[dtype]['inputfile']} "
                f"was truncated by sosreport. Some {dtype} may be missing.")

        sortby_col = self.conf.dynflowdata[dtype]['sortby']
        reverse = self.conf.dynflowdata[dtype]['reverse']
        expected_headers = self.conf.dynflowdata[dtype]['headers']

        # Read first line to check if it has headers
        with open(inputfile, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        has_headers = any(header in first_line for header in expected_headers)

        # Use pandas for faster CSV reading
        if has_headers:
            df = pd.read_csv(
                inputfile,
                encoding='utf-8',
                engine='c',
                na_filter=False,
                low_memory=False
            )
        else:
            # No headers - use schema to assign column names
            df = pd.read_csv(
                inputfile,
                header=None,
                names=expected_headers,
                encoding='utf-8',
                engine='c',
                na_filter=False,
                low_memory=False
            )

        # Sort the dataframe if sort column exists
        if sortby_col in df.columns:
            df = df.sort_values(by=sortby_col, ascending=not reverse)
        else:
            self.util.debug(
                'W',
                f"{dtype}: sort column '{sortby_col}' not in CSV, "
                f"skipping sort. Available columns: {list(df.columns)}"
            )

        # Convert to list of lists (maintaining compatibility)
        return df.values.tolist()

    def get_dynflow_schema(self):
        # 24 is from Satellite 6.11
        # 25 is from Satellite 6.19
        if self.conf.dynflowdata['version'] in ["24", "25"]:
            self.conf.dynflowdata['tasks'] = {
                'inputfile': "/sos_commands/foreman/foreman_tasks_tasks",
                'sortby': 'started_at',
                'reverse': True,
                'dates': ['started_at', 'ended_at', 'state_updated_at'],
                'json': [],
                'headers': ['id', 'dtype', 'label', 'started_at', 'ended_at',
                            'state', 'result', 'external_id', 'parent_task_id',
                            'start_at', 'start_before', 'action', 'user_id',
                            'state_updated_at']
            }
            self.conf.dynflowdata['plans'] = {
                'inputfile': "/sos_commands/foreman/dynflow_execution_plans",
                'sortby': 'started_at',
                'reverse': True,
                'dates': [
                    'started_at',
                    'ended_at'],
                'json': [
                    'run_flow', 'finalize_flow',
                    'execution_history', 'step_ids'],
                'headers': [
                    'uuid', 'state', 'result', 'started_at', 'ended_at',
                    'real_time', 'execution_time', 'label', 'class',
                    'root_plan_step_id', 'run_flow', 'finalize_flow',
                    'execution_history', 'step_ids', 'data']
            }
            self.conf.dynflowdata['actions'] = {
                'inputfile': "/sos_commands/foreman/dynflow_actions",
                'sortby': 'caller_action_id',
                'reverse': False,
                'json': ['input', 'output'],
                'dates': [],
                'headers': [
                    'execution_plan_uuid', 'id',
                    'caller_execution_plan_id', 'caller_action_id',
                    'class', 'plan_step_id', 'run_step_id',
                    'finalize_step_id', 'data', 'input', 'output']
            }
            self.conf.dynflowdata['steps'] = {
                'inputfile': "/sos_commands/foreman/dynflow_steps",
                'sortby': 'started_at',
                'reverse': True,
                'json': ['children', 'error'],
                'dates': ['started_at', 'ended_at'],
                'headers': [
                    'execution_plan_uuid', 'id', 'action_id', 'state',
                    'started_at', 'ended_at', 'real_time',
                    'execution_time', 'progress_done', 'progress_weight',
                    'class', 'action_class', 'queue', 'error',
                    'children', 'data']
            }
            if self.conf.dynflowdata['version'] == "25":  # Satellite 6.19
                # last two fields changed position:
                # before: 'user_id', 'state_updated_at'
                self.conf.dynflowdata['tasks']['headers'] = [
                    'id', 'dtype', 'label', 'started_at',
                    'ended_at', 'state', 'result', 'external_id',
                    'parent_task_id', 'start_at', 'start_before',
                    'action', 'state_updated_at', 'user_id']
        else:
            print("ERROR: Dynflow schema version "
                  + f"{self.conf.dynflowdata['version']} is not supported. "
                  + "Please refer to README.")
            sys.exit(1)
