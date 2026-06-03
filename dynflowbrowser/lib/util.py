import datetime
import subprocess
import sys

import pytz


class Util:

    def __init__(self, debuglevel='W', error_callback=None) -> None:
        self.debuglevel = debuglevel
        self.error_callback = error_callback
        self.valid_date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            ]

    def debug(self, sev, msg):
        levels = {'D': 0,
                  'I': 1,
                  'W': 2,
                  'E': 3
                  }
        if levels[sev] >= levels[self.debuglevel]:
            formatted_msg = f"[{sev}] {str(msg)}"
            # For errors, use callback to show modal if available
            if sev == 'E' and self.error_callback:
                self.error_callback(formatted_msg)
                # Raise exception instead of sys.exit when callback is set
                raise RuntimeError(msg)
            print(formatted_msg + "\n", file=sys.stderr, flush=True)
        if sev == 'E' and not self.error_callback:
            sys.exit(1)

    def exec_command(self, cmd):
        self.debug("D", "execcommand: " + cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        stdout = str(stdout.decode("utf-8"))
        stderr = str(stderr.decode("utf-8"))
        if stderr != "":
            print(cmd + "\n" + stderr)
            sys.exit(1)
        return stdout

    def seconds_to_str(self, seconds):
        m = str(round(seconds / 60)) + "m"
        s = str(round(seconds % 60)) + "s"
        return m + s

    def to_timezone(self, tz, d):
        if d is None:
            return d
        to_zone = pytz.timezone(tz)
        from_zone = datetime.timezone.utc
        newd = d.replace(tzinfo=from_zone)
        dlocal = newd.astimezone(to_zone).replace(tzinfo=None)
        return dlocal

    def date_from_string(self, d):
        valid = self.valid_date_formats
        for v in valid:
            try:
                return datetime.datetime.strptime(d, v)
            except ValueError:
                continue
        # TODO: Fix dynflowparser to not output invalid dates like '1'
        # For now, log warning and return None to skip corrupt date fields
        self.debug('W', f"Invalid date value {d!r}, setting to NULL")
        return None

    def change_timezone(self, tz, d):
        if d is not None and d != "":
            parsed_date = self.date_from_string(d)
            if parsed_date is not None:
                return self.to_timezone(tz, parsed_date)
        return None
