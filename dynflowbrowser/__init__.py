import datetime

from dynflowbrowser.lib.configuration import Conf
from dynflowbrowser.lib.inputdynflow import InputDynflow
from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.search_parser import SearchParser
from dynflowbrowser.lib.util import Util


class DynflowBrowser:

    def __init__(self):
        # Initialize in TUI mode to skip console prompts
        self.conf = Conf(tui_mode=True)
        self.util = Util()
        self.input_dynflow = InputDynflow(self.conf)
        self.search_parser = SearchParser()

    def main(self):
        sqlite = OutputSQLite(self.conf)
        headers = self.conf.dynflowdata['tasks']['headers']
        dynflow = self.input_dynflow.read_dynflow('tasks')

        # Calculate date range if --task-days is specified
        if self.conf.args.task_days:
            dto = self.util.date_from_string(self.conf.sos['localtime'])
            dfrom = dto - datetime.timedelta(days=self.conf.args.task_days)
        else:
            # Default: all time
            dfrom = self.util.date_from_string('1974-04-10')
            dto = self.util.date_from_string('2999-01-01')
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
            # Filter by date range
            if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
                include_task = True

                # Filter by state if --state is specified
                if self.conf.args.state:
                    task_state = dline[headers.index('state')].lower()
                    if task_state != self.conf.args.state.lower():
                        include_task = False

                # Filter by result if --result is specified
                if include_task and self.conf.args.result:
                    task_result = dline[headers.index('result')].lower()
                    if task_result != self.conf.args.result.lower():
                        include_task = False

                # Filter by search query if --search is specified
                if include_task and self.conf.args.search:
                    conditions = self.search_parser.parse(
                        self.conf.args.search
                    )
                    if not self.search_parser.evaluate(
                            conditions, dline, headers):
                        include_task = False

                if include_task:
                    self.conf.dynflowdata['includedUUID'].append(
                        dline[headers.index('external_id')]
                    )
        # Route to UI - pass sqlite write responsibility to UI layer
        from dynflowbrowser.lib.ui.text.output import TextOutput
        output = TextOutput(self.conf)
        output.write(
            sqlite=sqlite,
            input_dynflow=self.input_dynflow
        )  # Blocking call - runs until user quits
