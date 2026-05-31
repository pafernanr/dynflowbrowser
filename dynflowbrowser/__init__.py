import datetime
import os
import time

from dynflowbrowser.lib.configuration import Conf
from dynflowbrowser.lib.inputdynflow import InputDynflow
from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.util import Util


class DynflowBrowser:

    def __init__(self):
        self.conf = Conf()
        self.util = Util(self.conf.args.debug)
        self.input_dynflow = InputDynflow(self.conf)

    def main(self):
        sqlite = OutputSQLite(self.conf)
        headers = self.conf.dynflowdata['tasks']['headers']
        dynflow = self.input_dynflow.read_dynflow('tasks')
        if self.conf.args.last_n_days:
            dto = self.util.date_from_string(self.conf.sos['localtime'])
            dfrom = dto - datetime.timedelta(days=self.conf.args.last_n_days)
            self.conf.args.date_from = dfrom
            self.conf.args.date_to = dto
        else:
            dfrom = self.conf.args.date_from
            dto = self.conf.args.date_to
        # workaround for disordered fields on some csv files
        if " " not in dynflow[2][13]:
            self.conf.dynflowdata['tasks']['headers'] = [
                'id', 'dtype', 'label', 'started_at', 'ended_at',
                'state', 'result', 'external_id', 'parent_task_id',
                'start_at', 'start_before', 'action',
                'state_updated_at', 'user_id']
        # end workaround
        for i, dline in enumerate(dynflow):
            # exclude task if not between arguments dfrom and dto
            starts = "1974-04-10"
            ends = "2999-01-01"
            if 'started_at' in headers:
                istarts = headers.index('started_at')
                iends = headers.index('ended_at')
                if dline[istarts] != "":
                    starts = dline[istarts]
                if dline[iends] != "":
                    ends = dline[iends]
            starts = self.util.change_timezone(
                self.conf.sos['timezone'],
                starts)
            ends = self.util.change_timezone(
                self.conf.sos['timezone'],
                ends)
            if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
                if not self.conf.args.showall:
                    if dline[headers.index('result')] != 'success':
                        self.conf.dynflowdata['includedUUID'].append(
                            dline[headers.index('external_id')]
                        )
                else:
                    self.conf.dynflowdata['includedUUID'].append(
                        dline[headers.index('external_id')]
                        )
        # Write Tasks to SQLite
        if self.conf.writesql:
            for d in ['tasks', 'plans', 'actions', 'steps']:
                dynflow = self.input_dynflow.read_dynflow(d)
                sqlite.write(d, dynflow)
            # Create indexes after all data is inserted for better performance
            sqlite.create_indexes()

        # Route to appropriate UI based on flags
        # All interfaces now use text UI - either with welcome or direct mode
        from dynflowbrowser.lib.ui.text.output import TextOutput
        output = TextOutput(self.conf)
        output.write()  # Blocking call - runs until user quits
