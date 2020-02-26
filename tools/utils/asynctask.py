#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#======================================================================
#
# asynctask.py - 
#
# Created by skywind on 2020/02/25
# Last Modified: 2020/02/25 21:55:54
#
#======================================================================
from __future__ import print_function, unicode_literals
import sys
import os
import copy
import fnmatch
import pprint


#----------------------------------------------------------------------
# 2/3 compatible
#----------------------------------------------------------------------
if sys.version_info[0] >= 3:
    unicode = str
    long = int


UNIX = (sys.platform[:3] != 'win') and True or False


#----------------------------------------------------------------------
# macros
#----------------------------------------------------------------------
MACROS_HELP = { 
	'VIM_FILEPATH': 'File name of current buffer with full path',
	'VIM_FILENAME': 'File name of current buffer without path',
	'VIM_FILEDIR': 'Full path of current buffer without the file name',
	'VIM_FILEEXT': 'File extension of current buffer',
	'VIM_FILETYPE': 'File type (value of &ft in vim)',
    'VIM_FILENOEXT': # noqa: E261
      'File name of current buffer without path and extension',
	'VIM_PATHNOEXT':
      'Current file name with full path but without extension',
	'VIM_CWD': 'Current directory',
	'VIM_RELDIR': 'File path relativize to current directory',
	'VIM_RELNAME': 'File name relativize to current directory',
	'VIM_ROOT': 'Project root directory',
	'VIM_PRONAME': 'Name of current project root directory',
	'VIM_DIRNAME': "Name of current directory",
	'VIM_CWORD': 'Current word under cursor',
	'VIM_CFILE': 'Current filename under cursor',
	'VIM_CLINE': 'Cursor line number in current buffer',
	'VIM_GUI': 'Is running under gui ?',
	'VIM_VERSION': 'Value of v:version',
	'VIM_COLUMNS': "How many columns in vim's screen",
	'VIM_LINES': "How many lines in vim's screen", 
	'VIM_SVRNAME': 'Value of v:servername for +clientserver usage',
	'WSL_FILEPATH': '(WSL) File name of current buffer with full path',
	'WSL_FILENAME': '(WSL) File name of current buffer without path',
	'WSL_FILEDIR': '(WSL) Full path of current buffer without the file name',
	'WSL_FILEEXT': '(WSL) File extension of current buffer',
    'WSL_FILENOEXT':  # noqa: E261
      '(WSL) File name of current buffer without path and extension', 
	'WSL_PATHNOEXT':
	  '(WSL) Current file name with full path but without extension',
	'WSL_CWD': '(WSL) Current directory',
	'WSL_RELDIR': '(WSL) File path relativize to current directory',
	'WSL_RELNAME': '(WSL) File name relativize to current directory',
	'WSL_ROOT': '(WSL) Project root directory',
	'WSL_CFILE': '(WSL) Current filename under cursor',
}



#----------------------------------------------------------------------
# file type detection (as filetype in vim)
#----------------------------------------------------------------------
FILE_TYPES = {
    'text': '*.txt',
    'c': '*.[cChH],.[cChH].in',
    'cpp': '*.[cChH]pp,*.hh,*.[ch]xx,*.cc,*.cc.in,*.cpp.in,*.hh.in,*.cxx.in',
    'python': '*.py,*.pyw',
    'vim': '*.vim',
    'asm': '*.asm,*.s,*.S',
    'java': '*.java,*.jsp,*.jspx',
    'javascript': '*.js',
    'json': '*.json',
    'perl': '*.pl',
    'go': '*.go',
    'haskell': '*.hs',
    'sh': '*.sh',
    'lua': '*.lua',
    'bash': '*.bash',
    'make': '*.mk,*.mak,[Mm]akefile,[Gg][Nn][Uu]makefile,[Mm]akefile.in',
    'cmake': 'CMakeLists.txt',
    'zsh': '*.zsh',
    'fish': '*.fish',
    'ruby': '*.rb',
    'php': '*.php,*.php4,*.php5',
    'ps1': '*.ps1',
    'cs': '*.cs',
    'erlang': '*.erl,*.hrl',
    'html': '*.html,*.htm',
    'kotlin': '*.kt,*.kts',
    'markdown': '*.md,*.markdown,*.mdown,*.mkdn',
    'rust': '*.rs',
    'scala': '*.scala',
    'swift': '*.swift',
    'dosini': '*.ini',
    'yaml': '*.yaml,*.yml',
}


#----------------------------------------------------------------------
# call program and returns output (combination of stdout and stderr)
#----------------------------------------------------------------------
def execute(args, shell = False, capture = False):
    import sys, os  # noqa: F811
    parameters = []
    cmd = None
    if not isinstance(args, list):
        import shlex
        cmd = args
        if sys.platform[:3] == 'win':
            ucs = False
            if sys.version_info[0] < 3:
                if not isinstance(cmd, str):
                    cmd = cmd.encode('utf-8')
                    ucs = True
            args = shlex.split(cmd.replace('\\', '\x00'))
            args = [ n.replace('\x00', '\\') for n in args ]
            if ucs:
                args = [ n.decode('utf-8') for n in args ]
        else:
            args = shlex.split(cmd)
    for n in args:
        if sys.platform[:3] != 'win':
            replace = { ' ':'\\ ', '\\':'\\\\', '\"':'\\\"', '\t':'\\t',
                '\n':'\\n', '\r':'\\r' }
            text = ''.join([ replace.get(ch, ch) for ch in n ])
            parameters.append(text)
        else:
            if (' ' in n) or ('\t' in n) or ('"' in n): 
                parameters.append('"%s"'%(n.replace('"', ' ')))
            else:
                parameters.append(n)
    if cmd is None:
        cmd = ' '.join(parameters)
    if sys.platform[:3] == 'win' and len(cmd) > 255:
        shell = False
    if shell and (not capture):
        os.system(cmd)
        return b''
    elif (not shell) and (not capture):
        import subprocess
        if 'call' in subprocess.__dict__:
            subprocess.call(args)
            return b''
    import subprocess
    if 'Popen' in subprocess.__dict__:
        p = subprocess.Popen(args, shell = shell,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE, 
                stderr = subprocess.STDOUT)
        stdin, stdouterr = (p.stdin, p.stdout)
    else:
        p = None
        stdin, stdouterr = os.popen4(cmd)
    stdin.close()
    text = stdouterr.read()
    stdouterr.close()
    if p: p.wait()
    if not capture:
        sys.stdout.write(text)
        sys.stdout.flush()
        return b''
    return text


#----------------------------------------------------------------------
# read_ini
#----------------------------------------------------------------------
def load_ini_file (ininame, codec = None):
    if not ininame:
        return False
    elif not os.path.exists(ininame):
        return False
    try:
        content = open(ininame, 'rb').read()
    except IOError:
        content = b''
    if content[:3] == b'\xef\xbb\xbf':
        text = content[3:].decode('utf-8')
    elif codec is not None:
        text = content.decode(codec, 'ignore')
    else:
        codec = sys.getdefaultencoding()
        text = None
        for name in [codec, 'gbk', 'utf-8']:
            try:
                text = content.decode(name)
                break
            except:
                pass
        if text is None:
            text = content.decode('utf-8', 'ignore')
    if sys.version_info[0] < 3:
        import StringIO
        import ConfigParser
        sio = StringIO.StringIO(text)
        cp = ConfigParser.ConfigParser()
        cp.readfp(sio)
    else:
        import configparser
        cp = configparser.ConfigParser(interpolation = None,
                strict = False)
        cp.read_string(text)
    config = {}
    for sect in cp.sections():
        section = sect.strip()
        config[section] = {}
        for key, val in cp.items(sect):
            config[section][key.strip()] = val.strip()
    return config


#----------------------------------------------------------------------
# OBJECT：enchanced object
#----------------------------------------------------------------------
class OBJECT (object):
    def __init__ (self, **argv):
        for x in argv: self.__dict__[x] = argv[x]
    def __getitem__ (self, x):
        return self.__dict__[x]
    def __setitem__ (self, x, y):
        self.__dict__[x] = y
    def __delitem__ (self, x):
        del self.__dict__[x]
    def __contains__ (self, x):
        return self.__dict__.__contains__(x)
    def __len__ (self):
        return self.__dict__.__len__()
    def __repr__ (self):
        line = [ '%s=%s'%(k, repr(v)) for k, v in self.__dict__.items() ]
        return 'OBJECT(' + ', '.join(line) + ')'
    def __str__ (self):
        return self.__repr__()
    def __iter__ (self):
        return self.__dict__.__iter__()


#----------------------------------------------------------------------
# Terminal Output
#----------------------------------------------------------------------
class PrettyText (object):

    def __init__ (self):
        self.isatty = sys.stdout.isatty()
        self.names = self.__init_names()
        self.handle = None

    def __init_win32 (self):
        if sys.platform[:3] != 'win':
            return -1
        self.handle = None
        try: import ctypes
        except: return 0
        kernel32 = ctypes.windll.LoadLibrary('kernel32.dll')
        self.kernel32 = kernel32
        GetStdHandle = kernel32.GetStdHandle
        SetConsoleTextAttribute = kernel32.SetConsoleTextAttribute
        GetStdHandle.argtypes = [ ctypes.c_uint32 ]
        GetStdHandle.restype = ctypes.c_size_t
        SetConsoleTextAttribute.argtypes = [ ctypes.c_size_t, ctypes.c_uint16 ]
        SetConsoleTextAttribute.restype = ctypes.c_long
        self.handle = GetStdHandle(0xfffffff5)
        self.GetStdHandle = GetStdHandle
        self.SetConsoleTextAttribute = SetConsoleTextAttribute
        self.GetStdHandle = GetStdHandle
        return 0

    # init names
    def __init_names (self):
        ansi_names = ['black', 'red', 'green', 'yellow', 'blue', 'purple']
        ansi_names += ['cyan', 'white']
        names = {}
        for i, name in enumerate(ansi_names):
            names[name] = i
            names[name.upper()] = i + 8
        names['reset'] = -1
        names['RESET'] = -1
        return names

    # set color
    def set_color (self, color, stderr = False):
        if not self.isatty:
            return 0
        if isinstance(color, str):
            color = self.names.get(color, -1)
        elif sys.version_info[0] < 3:
            if isinstance(color, unicode):
                color = self.names.get(color, -1)
        if sys.platform[:3] == 'win':
            if self.handle is None:
                self.__init_win32()
            if color < 0: color = 7
            result = 0
            if (color & 1): result |= 4
            if (color & 2): result |= 2
            if (color & 4): result |= 1
            if (color & 8): result |= 8
            if (color & 16): result |= 64
            if (color & 32): result |= 32
            if (color & 64): result |= 16
            if (color & 128): result |= 128
            self.SetConsoleTextAttribute(self.handle, result)
        else:
            fp = (not stderr) and sys.stdout or sys.stderr
            if color >= 0:
                foreground = color & 7
                background = (color >> 4) & 7
                bold = color & 8
                t = bold and "01;" or ""
                if background:
                    fp.write("\033[%s3%d;4%dm"%(t, foreground, background))
                else:
                    fp.write("\033[%s3%dm"%(t, foreground))
            else:
                fp.write("\033[0m")
            fp.flush()
        return 0

    def echo (self, color, text, stderr = False):
        self.set_color(color, stderr)
        if stderr:
            sys.stderr.write(text)
            sys.stderr.flush()
        else:
            sys.stdout.write(text)
            sys.stdout.flush()
        self.set_color(-1, stderr)
        return 0

    def print (self, color, text):
        return self.echo(color, text + '\n')

    def tabulify (self, rows):
        colsize = {}
        maxcol = 0
        if not rows:
            return -1
        for row in rows:
            maxcol = max(len(row), maxcol)
            for col, item in enumerate(row):
                if isinstance(item, list) or isinstance(item, tuple):
                    text = str(item[1])
                else:
                    text = str(item)
                size = len(text)
                if col not in colsize:
                    colsize[col] = size
                else:
                    colsize[col] = max(size, colsize[col])
        if maxcol <= 0:
            return ''
        last_color = -100
        for row in rows:
            for col, item in enumerate(row):
                csize = colsize[col]
                color = -1
                if isinstance(item, list) or isinstance(item, tuple):
                    color = item[0]
                    text = str(item[1])
                else:
                    text = str(item)
                text = str(text)
                padding = 2 + csize - len(text)
                pad1 = 1
                pad2 = padding - pad1
                output = (' ' * pad1) + text + (' ' * pad2)
                if last_color != color:
                    self.set_color(color)
                    last_color = color
                sys.stdout.write(output)
                sys.stdout.flush()
            sys.stdout.write('\n')
        self.set_color(-1)
        return 0

    def error (self, text, code = -1):
        self.echo('RED', 'Error: ', True)
        self.echo(-1, text + '\n', True)
        sys.exit(code)
        return 0

    def warning (self, text):
        self.echo('red', 'Warning: ', True)
        self.echo(-1, text + '\n', True)
        return 0



#----------------------------------------------------------------------
# internal
#----------------------------------------------------------------------
pretty = PrettyText()



#----------------------------------------------------------------------
# configure
#----------------------------------------------------------------------
class configure (object):

    def __init__ (self, path = None):
        self.win32 = sys.platform[:3] == 'win' and True or False
        self._cache = {}
        if not path:
            path = os.getcwd()
        else:
            path = os.path.abspath(path)
        if not os.path.exists(path):
            raise IOError('invalid path: %s'%path)
        if os.path.isdir(path):
            self.home = path
            self.target = 'dir'
        else:
            self.home = os.path.dirname(path)
            self.target = 'file'
        self.path = path
        self.filetype = None
        self.mark = '.git,.svn,.project,.hg,.root'
        if 'VIM_TASK_ROOTMARK' in os.environ:
            mark = os.environ['VIM_TASK_ROOTMARK'].strip()
            if mark:
                self.mark = mark
        mark = [ n.strip() for n in self.mark.split(',') ]
        self.root = self.find_root(self.home, mark, True)
        self.tasks = {}
        self.environ = {}
        self.config = {}
        self._load_config()
        if self.target == 'file':
            self.filetype = self.match_ft(self.path)
        self.feature = {}

    def read_ini (self, ininame, codec = None):
        ininame = os.path.abspath(ininame)
        key = ininame
        if self.win32:
            key = ininame.replace("\\", '/').lower()
        if key in self._cache:
            return self._cache[key]
        config = load_ini_file(ininame)
        self._cache[key] = config
        inihome = os.path.dirname(ininame)
        for sect in config:
            section = config[sect]
            for key in list(section.keys()):
                val = section[key]
                val = val.replace('$(VIM_INIHOME)', inihome)
                val = val.replace('$(VIM_ININAME)', ininame)
                section[key] = val
        return config

    def find_root (self, path, markers = None, fallback = False):
        if markers is None:
            markers = ('.git', '.svn', '.hg', '.project', '.root')
        if path is None:
            path = os.getcwd()
        path = os.path.abspath(path)
        base = path
        while True:
            parent = os.path.normpath(os.path.join(base, '..'))
            for marker in markers:
                test = os.path.join(base, marker)
                if os.path.exists(test):
                    return base
            if os.path.normcase(parent) == os.path.normcase(base):
                break
            base = parent
        if fallback:
            return path
        return None

    def check_environ (self, key):
        if key in os.environ:
            if os.environ[key].strip():
                return True
        return False

    def extract_list (self, text):
        items = []
        for item in text.split(','):
            item = item.strip('\r\n\t ')
            if not item:
                continue
            items.append(item)
        return items

    def option (self, section, key, default):
        if section not in self.config:
            return default
        sect = self.config[section]
        return sect.get(key, default).strip()

    def _load_config (self):
        self.system = self.win32 and 'win32' or 'linux'
        self.profile = 'debug'
        self.cfg_name = '.tasks'
        self.rtp_name = 'tasks.ini'
        self.extra_config = []
        self.config = {}
        # load ~/.config
        name = os.path.expanduser('~/.config')
        if self.check_environ('XDG_CONFIG_HOME'):
            name = os.environ['XDG_CONFIG_HOME']
        name = os.path.join(name, 'asynctask/asynctask.ini')
        name = os.path.abspath(name)
        if os.path.exists(name):
            self.config = self.read_ini(name)
        if 'default' not in self.config:
            self.config['default'] = {}
        setting = self.config['default']
        self.system = setting.get('system', self.system).strip()
        self.cfg_name = setting.get('cfgname', self.cfg_name).strip()
        self.rtp_name = setting.get('rtpname', self.rtp_name).strip()
        if 'extras' in setting:
            for path in self.extract_list(setting['extra']):
                if os.path.exists(path):
                    self.extra_config.append(os.path.abspath(path))
        # load from environment
        if self.check_environ('VIM_TASK_SYSTEM'):
            self.system = os.environ['VIM_TASK_SYSTEM']
        if self.check_environ('VIM_TASK_PROFILE'):
            self.profile = os.environ['VIM_TASK_PROFILE']
        if self.check_environ('VIM_TASK_CFG_NAME'):
            self._cfg_name = os.environ['VIM_TASK_CFG_NAME']
        if self.check_environ('VIM_TASK_RTP_NAME'):
            self._rtp_name = os.environ['VIM_TASK_RTP_NAME']
        if self.check_environ('VIM_TASK_EXTRA_CONFIG'):
            extras = os.environ['VIM_TASK_EXTRA_CONFIG']
            for path in self.extract_list(extras):
                if os.path.exists(path):
                    self.extra_config.append(os.path.abspath(path))
        return 0

    def trinity_split (self, text):
        p1 = text.find(':')
        p2 = text.find('/')
        if p1 < 0 and p2 < 0:
            return [text, '', '']
        parts = text.replace('/', ':').split(':')
        if p1 >= 0 and p2 >= 0:
            if p1 < p2:
                return [parts[0], parts[1], parts[2]]
            else:
                return [parts[0], parts[2], parts[1]]
        elif p1 >= 0 and p2 < 0:
            return [parts[0], parts[1], '']
        elif p1 < 0 and p2 >= 0:
            return [parts[0], '', parts[1]]
        return [text, '', '']

    def config_merge (self, target, source, ininame, mode):
        special = []
        for key in source:
            if ':' in key:
                special.append(key)
            elif '/' in key:
                special.append(key)
            elif key != '*':
                target[key] = source[key]
                if ininame:
                    target[key]['__name__'] = ininame
                if mode:
                    target[key]['__mode__'] = mode
        for key in special:
            parts = self.trinity_split(key)
            parts = [ n.strip('\r\n\t ') for n in parts ]
            name = parts[0]
            if parts[1]:
                if self.profile != parts[1]:
                    continue
            if parts[2]:
                feature = self.feature.get(parts[2], False)
                if not feature:
                    continue
            target[name] = source[key]
            if ininame:
                target[name]['__name__'] = ininame
            if mode:
                target[name]['__mode__'] = mode
        return 0

    # search for global configs
    def collect_rtp_config (self):
        names = []
        t = os.path.join(os.path.expanduser('~/.vim'), self.rtp_name)
        if os.path.exists(t):
            names.append(os.path.abspath(t))
        for path in self.extra_config:
            if os.path.exists(path):
                names.append(os.path.abspath(path))
        for name in names:
            obj = self.read_ini(name)
            self.config_merge(self.tasks, obj, name, 'global')        
        return 0

    # search parent
    def search_parent (self, path):
        output = []
        path = os.path.abspath(path)
        while True:
            parent = os.path.normpath(os.path.join(path, '..'))
            output.append(path)
            if os.path.normcase(path) == os.path.normcase(parent):
                break
            path = parent
        return output

    # search for local configs
    def collect_local_config (self):
        names = self.search_parent(self.home)
        for name in names:
            t = os.path.abspath(os.path.join(name, self.cfg_name))
            if not os.path.exists(t):
                continue
            obj = self.read_ini(t)
            self.config_merge(self.tasks, obj, t, 'local')
        return 0

    # merge global and local config
    def load_tasks (self):
        self.tasks = {}
        self.collect_rtp_config()
        self.collect_local_config()
        return 0

    # extract file type
    def match_ft (self, name):
        name = os.path.abspath(name)
        name = os.path.split(name)[-1]
        detect = {}
        for n in FILE_TYPES:
            detect[n] = FILE_TYPES[n]
        if 'filetypes' in self.config:
            filetypes = self.config['filetypes']
            for n in filetypes:
                detect[n] = filetypes[n]
        for ft in detect:
            rules = [ n.strip() for n in detect[ft].split(',') ]
            for rule in rules:
                if not rule:
                    continue
                if fnmatch.fnmatch(name, rule):
                    return ft
        return None

    def expand_macros (self):
        macros = {}
        return macros
        

#----------------------------------------------------------------------
# manager
#----------------------------------------------------------------------
class TaskManager (object):

    def __init__ (self, path):
        self.config = configure(path)

    def command_select (self, task, filetype):
        command = task.get('command', '')
        for key in task:
            p1 = key.find(':')
            p2 = key.find('/')
            if p1 < 0 and p2 < 0:
                continue
            parts = self.config.trinity_split(key)
            parts = [ n.strip('\r\n\t ') for n in parts ]
            if parts[0] != 'command':
                continue
            if parts[1]:
                check = 0
                for ft in parts[1].split(','):
                    ft = ft.strip()
                    if ft == filetype:
                        check = 1
                        break
                if check == 0:
                    continue
            if parts[2]:
                if parts[2] != self.config.system:
                    continue
            return task[key]
        return command

    def command_check (self, command, cwd):
        return 0

    def task_run (self, taskname):
        if taskname not in self.config.tasks:
            pretty.error('not find task [' + taskname + ']')
            return -2
        task = self.config.tasks[taskname]
        ininame = task.get('__ininame__', '<unknow>')
        source = 'task [' + taskname + '] from ' + ininame
        filetype = ''
        command = self.command_select(task, filetype)
        if not command:
            pretty.error('no command defined in ' + source)
            return -3
        os.system(command)
        return 0


#----------------------------------------------------------------------
# testing suit
#----------------------------------------------------------------------
if __name__ == '__main__':
    def test1():
        c = configure('d:/acm/github/vim/autoload')
        # cfg = c.read_ini(os.path.expanduser('~/.vim/tasks.ini'))
        # pprint.pprint(cfg)
        print(c.root)
        print(c.trinity_split('command:vim/win32'))
        print(c.trinity_split('command/win32:vim'))
        print(c.trinity_split('command/win32'))
        print(c.trinity_split('command:vim'))
        print(c.trinity_split('command'))
        pprint.pprint(c.tasks)
        # print(c.search_parent('d:/acm/github/vim/autoload/quickui'))
        return 0
    def test2():
        # tm = TaskManager('d:/acm/github/vim/autoload/quickui/generic.vim')
        tm = TaskManager('')
        print(tm.config.root)
        pprint.pprint(tm.config.tasks)
    def test3():
        # pretty.print('cyan', 'hello')
        rows = []
        rows.append(['Name', 'Gender'])
        rows.append([('red', 'Zhang Jia'), 'male'])
        rows.append(['Lin Ting Ting', 'female'])
        # print('fuck you')
        print('hahahah')
        pretty.tabulify(rows)
        pretty.error('something error')
        return 0
    def test4():
        tm = TaskManager('d:/acm/github/kcp/test.cpp')
        print(tm.config.filetype)
        tm.task_run('task2')
    test4()


