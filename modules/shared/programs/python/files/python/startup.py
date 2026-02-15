import os
import sys

if sys.version_info < (3, 13) and not sys.flags.no_site and not sys.flags.isolated:

    def register_readline():
        import atexit

        try:
            import readline
            import rlcompleter
        except ImportError:
            return

        readline_doc = getattr(readline, "__doc__", "")
        if readline_doc is not None and "libedit" in readline_doc:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

        try:
            readline.read_init_file()
        except OSError:
            pass

        if readline.get_current_history_length() == 0:
            history = os.path.expanduser(os.path.expandvars("$PYTHON_HISTORY"))
            try:
                readline.read_history_file(history)
            except OSError:
                pass

            def write_history():
                try:
                    readline.write_history_file(history)
                except OSError:
                    pass

            atexit.register(write_history)

    setattr(sys, "__interactivehook__", register_readline)
