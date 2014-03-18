import subprocess


class ExecutionResult(object):
    def __init__(self, return_code, stdout, stderr):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class RealExecutor(object):
    def run(self, args):
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return ExecutionResult(
            return_code=proc.returncode,
            stdout=out,
            stderr=err)


class PrintExecutor(object):
    def __init__(self, stream):
        self.stream = stream

    def run(self, args):
        self.stream.write(' '.join(args) + '\n')
        return ExecutionResult(
            return_code=0,
            stdout='',
            stderr='')
