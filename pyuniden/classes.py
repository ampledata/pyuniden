#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Uniden Scanner Python API"""

__copyright__ = 'Copyright (C) 2014-2015 Anton Komarov'


import logging
import time

import serial
import yaml


import pyuniden.constants


class UnidenScannerError(Exception):
    pass

class UnidenCommandError(UnidenScannerError):
    pass

class ModulationError(UnidenScannerError):
    pass

class BScreenError(UnidenScannerError):
    pass


class UnidenScanner(object):

    ERR_LIST = ('NG','ORER','FER','ERR','')

    logger = logging.getLogger(__name__)
    logger.setLevel(pyuniden.constants.LOG_LEVEL)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(pyuniden.constants.LOG_LEVEL)
    console_handler.setFormatter(pyuniden.constants.LOG_FORMAT)

    logger.addHandler(console_handler)
    logger.propagate = False

    def __init__(self, port, speed=None):
        self.port = port
        self.speed = speed or '115200'
        self.serial=None
        self.model=None
        self.version=None
        self.program_mode=False
        self.system_index_head=None
        self.system_index_tail=None
        #self.settings=Settings(self)
        self.settings = {}
        self.quick_lockout=()
        self.systems={}
        #self.searches=Search(self)
        self.searches = {}
        self.free_memory_block=None
        self.used_memory_block={}
        self.default_band_coverage = ()

        self.open(self.port, self.speed)

    def open(self, port, speed):
        """
        Open scanner method, accepts port and speed, timeout is set for 100ms
        """
        try:
            self.serial=serial.Serial(port,speed,timeout=0.1)
        except serial.SerialException:
            self.logger.error('Error opening serial port %s!', port)

    def close(self):
        if self.serial.isOpen():
            self.serial.close()

    def __del__(self):
        self.close()

    def raw(self, cmd):
        """Wrapper for raw scanner command"""
        f2 = 'OK'
        self.logger.debug('cmd=%s', cmd)

        self.serial.write(''.join([cmd, '\r']))
        res = (self.serial.readall()).strip('\r')
        self.logger.debug('res=%s', res)

        if res.count(',') == 1:
            f2 = res.split(',')[1]
        else:
            f2 = res

        if f2 in self.ERR_LIST:
            raise UnidenCommandError, "Scanner returned ERR '%s'" % f2
        else:
            return res

    def get_model(self):
        """Returns Model Information."""
        res = self.raw('MDL')
        (cmd, self.model) = res.split(',')

    def get_version(self):
        """Returns Firmware Version."""
        res = self.raw('VER')
        (cmd, self.version) = res.split(',')

    def get_rssi_power(self):
        """Returns current RSSI level and its frequency.
        The order of the frequency digits is from 1 GHz digit to 100 Hz digit.

        RSSI        RSSI A/D Value (0-1023)
        FRQ        The order of the frequency digits is from 1 GHz digit to 100 Hz digit.
        """
        res = self.raw('PWR')
        (cmd, rssi, frq)=res.split(',')
        dict = {'rssi': rssi, 'frq': frq}
        return dict

    def get_reception_status(self):
        """
        Gets reception status.

        The Scanner returns GLG,,,,,,,,,[\r] until it detects a frequency or a TGID.

        FRQ/TGID    Frequency or TGID
        MOD        Modulation (AM/FM/NFM/WFM/FMB)
        ATT        Attenuation (0:OFF / 1:ON)
        CTCSS/DCS    CTCSS/DCS Status (0-231)
        NAME1        System, Site or Search Name
        NAME2        Group Name
        NAME3        Channel Name
        SQL        Squelch Status (0:CLOSE / 1:OPEN)
        MUT        Mute Status (0:OFF / 1:ON)
        SYS_TAG        Current system number tag (0-999/NONE)
        CHAN_TAG    Current channel number tag (0-999/NONE)
        P25NAC        P25 NAC Status ( 0-FFF: 0-FFF / NONE: Nac None)

        """
        ret_keys = [
            'frq_tgid', 'mod', 'att', 'ctcss_dcs', 'name1', 'name2',
            'name3', 'sql', 'mute', 'sys_tag', 'chan_tag', 'p25nac'
        ]
        res = self.raw('GLG')
        return dict(zip(ret_keys, res.split(',')[1:]))

    def get_current_status(self):
        """Returns current scanner status.

        DSP_FORM    Display Form (4 - 8dight:########) (each # is 0 or 1) 0 means Small Font / 1 means Large Font.
        Lx_CHAR        Linex Characters 16char (fixed length)
        Lx_MODE        Linex Display Mode 16char
        SQL         Squelch Status (0:CLOSE / 1:OPEN)
        MUT         Mute Status (0:OFF / 1:ON)
        BAT         Battery Low Status (0:No Alert / 1:Alert)
        WAT        Weather Alert Status (0:No Alert / 1: Alert / $$$: Alert SAME CODE)
        SIG_LVL        Signal Level (0–5)
        BK_COLOR    Backlight Color (OFF,BLUE,RED,MAGENTA,GREEN,CYAN,YELLOW,WHITE)
        BK_DIMMER    Backlight Dimmer (0:OFF / 1:Low / 2:Middle / 3:High )
        """
        ret_keys = [
            'dsp_form', 'lx_char', 'lx_mode', 'sql', 'mut', 'bat', 'wat',
            'sig_lvl', 'bk_color', 'bk_dimmer'
        ]
        res = self.raw('STS')
        return dict(zip(ret_keys, res.split(',')[1:]))

        #l=res.split(",")
        #n=len(l[1])
        #cm=l[2:n*2+1]
        #while (len(cm)<17): cm.append('')
        #dict={'dsp_form':l[0], 'char': tuple(cm[0::2]), 'mode': tuple(cm[1::2]),
        #    'sql':l[-9], 'mut':l[-8], 'bat':l[-7], 'wat':l[-6], 'rsv1':l[-5],
        #    'rsv2':l[-4], 'sig_lvl':l[-3], 'bk_color':l[-2], 'bk_dimmer':l[-1]}
        #return dict

    def push_key(self, mode, key):
        """push_key method is used to push keys on the scanner

        Keys:
         M : menu
         F : func
         H : hold
         S : scan/srch
         L : lo
         1 : 1
         2 : 2
         3 : 3
         4 : 4
         5 : 5
         6 : 6
         7 : 7
         8 : 8
         9 : 9
         0 : 0
         .(dot) : dot/no/pri
         E : E/yes/gps
         > : vright * Set "P" to KEY_MODE.
         < : vleft * Set "P" to KEY_MODE.
         ^ : vpush
         P : pwr/light/lock

        Modes:
         P : press
         L : long (press)
         H : hold (Press and Hold until Release receive)
         R : release (Cancel Hold state)
         """

        keys = { "menu":"M", "func":"F", "hold":"H", "scan":"S", "srch":"S",
             "lo":"L", "1":"1", "2":"2", "3":"3", "4":"4", "5":"5",
             "6":"6", "7":"7", "8":"8", "9":"9", "0":"0", "dot":".",
             "no":".", "pri":".", "E":"E", "yes":"E", "gps":"E", "pwr":"P",
             "vright":">", "vleft":"<", "vpush":"^", "lock":"P", "light":"P" }

        modes = { "press":"P", "long":"L", "hold":"H", "release":"R" }

        cmd = ",".join(['KEY',keys[key],modes[mode]])
        res = self.raw(cmd)

    def set_quick_search_hold(self, frq, mod="AUTO", att=0, dly=2,
                    code_srch=0, bsc="0000000000000000",
                    rep=0, agc_analog=0, agc_digital=0,
                    p25waiting=200):
        """This command is invalid when the scanner is in Menu Mode, during Direct Entry operation,
        during Quick Save operation.
        FUNCTION
        UASD specifies arbitrary frequency and changes to Quick Search Hold (VFO) mode.
        Parameter, such as STP, changes the contents of Srch/CloCall option.
        Note: Even when only [FRQ] parameter is set, this command will work.

        FRQ        Frequency (The right frequency)
        MOD        Modulation (AUTO/AM/FM/NFM/WFM/FMB)
        ATT        Attenuation (0:OFF / 1:ON)
        DLY        Delay Time (-10,-5,-2,0,1,2,5,10,30)
        CODE_SRCH    CTCSS/DCS/P25 NAC Search (0:OFF / 1: CTCSS/DCS / 2: P25 NAC Search)
        BSC        Broadcast Screen (16digit: ########・・#)
        (each # is 0 or 1)                         ||||||||・・+- Band10
        0 means OFF                   ||||||||       :
        1 means ON                    |||||||+---- Band 2
                                                   ||||||+----- Band 1
                                                   |||||+------ Reserve
                                                   ||||+------- NOAA WX
                                                   |||+-------- VHF TV
                                                   ||+--------- UHF TV
                                                   |+---------- FM
                                                   +----------- Pager
        REP        Repeater Find (0:OFF / 1:ON)
        AGC_ANALOG    AGC Setting for Analog Audio (0:OFF / 1:ON)
        AGC_DIGITAL    AGC Setting for Digital Audio (0:OFF / 1:ON)
        P25WAITING    P25 Waiting time (0,100,200,300, .... , 900,1000) ms
        """
        rsv=''

        frq=''.join([frq.split('.')[0].rjust(4,'0'),
             frq.split('.')[1].ljust(4,'0')])

        if mod not in mod_values:
            raise ModulationError

        if (len(bsc)<>16 or len(bsc.replace('0','').replace('1',''))):
            raise BScreenError

        cmd=",".join(['QSH',frq,rsv,mod,str(att),str(dly),rsv,str(code_srch),bsc,str(rep),
                    rsv,str(agc_analog),str(agc_digital),str(p25waiting)])

        res = self.raw(cmd)

    def set_curfrq_reception_status(self, frq, mod="AUTO", att=0, dly=2,
                    code_srch=0, bsc="0000000000000000",
                    rep=0, agc_analog=0, agc_digital=0,
                    p25waiting=200):
        """Set current frequency and get reception status.
        see set_quick_search_hold() for vars value descriptions."""

        rsv=''

        frq=''.join([frq.split('.')[0].rjust(4,'0'),
             frq.split('.')[1].ljust(4,'0')])

        if mod not in mod_values:
            raise ModulationError

        if (len(bsc)<>16 or len(bsc.replace('0','').replace('1',''))):
            raise BScreenError

        cmd=",".join(['QSC',frq,rsv,mod,str(att),str(dly),rsv,str(code_srch),bsc,str(rep),
                    rsv,str(agc_analog),str(agc_digital),str(p25waiting)])

        res = self.raw(cmd)

        (cmd,rssi,frq,sql) = res.split(",")

        return (rssi,frq,sql)

    def get_volume(self):
        """
        Gets volume level.
        'LEVEL        Volume Level ( 0 - 15 )'

        :returns: Volume level.
        :rtype: str
        """
        res = self.raw('VOL')
        (cmd, vol) = res.split(',')
        return vol

    def set_volume(self, vol):
        """
        Sets volume level.
        LEVEL        Volume Level ( 0 - 15 )'
        """
        cmd = ','.join(['VOL', str(vol)])
        res = self.raw(cmd)

    def get_squelch(self):
        """Get Squelch Level Settings

        LEVEL    Squelch Level (0:OPEN / 1-14 / 15:CLOSE)"""
        res = self.raw('SQL')

        (cmd,sql) = res.split(",")

        return sql

    def set_squelch(self, sql):
        """Set Squelch Level Settings

        LEVEL    Squelch Level (0:OPEN / 1-14 / 15:CLOSE)
        """
        cmd=",".join(['SQL',str(sql)])
        res = self.raw(cmd)

    def get_apco_data_settings(self):
        """Get APCO Data Settings

        ERR_RATE        Error Rate (from 0 to 99)
        """
        res = self.raw('P25')
        (cmd,rsv1,rsv2,err_rate) = res.split(",")
        return err_rate

    def set_apco_data_settings(self, p25):
        """Set APCO Data Settings

        ERR_RATE        Error Rate (from 0 to 99)
        """
        rsv=''
        cmd=",".join(['P25',rsv,rsv,str(p25)])
        res = self.raw(cmd)

    def jump_number_tag(self, sys_tag='NONE', chan_tag='NONE'):
        """When both [SYS_TAG] and [CHAN_TAG] are set as blank, scanner returns error.
        When [SYS_TAG] is set as blank, [CHAN_TAG] is set with a number tag, scanner jump to
        the channel number tag in current system.
        When [SYS_TAG] is set with a number tag, [CHAN_TAG] is set as blank, scanner jump to
        the first channel of the system number tag.

        SYS_TAG        System Number Tag (0-999/NONE)
        CHAN_TAG    Channel Number Tag (0-999/NONE)
        """
        cmd=",".join(['JNT',str(sys_tag),str(chan_tag)])
        res = self.raw(cmd)

    def get_battery_voltage(self):
        """A/D Value (0-1023)
        Battery Level[V] = (3.2[V] * #### * 2 )/1023
        """
        res = self.raw('BAV')
        (bav,ad_value) = res.split(',')
        return 3.2*float(ad_value)*2/1023

    def get_window_voltage(self):
        """A/D Value (0-255)
        Returns current window voltage and its frequency.
        The order of the frequency digits is from 1 GHz digit to 100 Hz digit.
        """
        res = self.raw('WIN')
        (win,ad_value,frq) = res.split(',')
        return (ad_value,frq)

    def enter_program_mode(self):
        """This command is invalid when the scanner is in Menu Mode, during Direct Entry operation,
        during Quick Save operation.

        The scanner goes to Program Mode.
        The scanner displays "Remote Mode" on first line and "Keypad Lock" on second line in
        Program Mode.
        """
        res = self.raw('PRG')
        self.program_mode=True

    def exit_program_mode(self):
        """The scanner exits from Program Mode.
        Then the scanner goes to Scan Hold Mode.
        """
        res = self.raw('EPG')
        self.program_mode = False

    def get_free_memory_blocks(self):
        """Returns the number of idle(free) memory block.
        ##### (not zero-padding)
        """
        res = self.raw('RMB')
        (rmb,self.free_memory_blocks) = res.split(',')

    def get_used_memory_blocks(self):
        """MEMORY_USED        The percent of memory that is used (0 - 100)
        SYS            The number of systems that is created (0 - 500)
        SITE            The number of sites that is created (0 - 1000)
        CHN            The number of channels that is created (0 – 25000)
        LOC            The number of location system that is created (0 – 1000)
        """
        res = self.raw('MEM')
        (rmb,memory_used,sys,site,chn,loc) = res.split(',')
        self.used_memory_blocks={'memory used':memory_used,
            'systems':sys, 'sites':site, 'channels':chn,
            'locations':loc}

    def get_default_band_coverage(self):
        """BNAD_NO        Band No (1-31) Band number of band coverage
        STP            Search Step
                                500: 5k 625: 6.25k 750: 7.5 k
                                833: 8.33k 1000 : 10k 1250 : 12.5k
                                1500 : 15k 2000 : 20k 2500 : 25k
                                5000 : 50k 10000 : 100k
        MOD            Modulation (AM / NFM / FM / WFM / FMB)
        """
        dfb = [0]

        for no in range(1,32):
            res = self.raw(','.join(['DBC',str(no)]))
            (dbc,step,mod) = res.split(',')
            dfb.append({'step':step, 'mod':mod})
        self.default_band_coverage = tuple(dfb)

    def get_system_settings(self):
        """Enters program mode and gets scanner settings data."""
        if not self.program_mode:
            self.enter_program_mode()
        self.settings.get_data()
        self.exit_program_mode()

    def get_scan_settings(self):
        """Enters program mode and gets scanner scan settings data recursively."""
        if not self.program_mode:
            self.enter_program_mode()
        sih = self.raw('SIH')
        sit = self.raw('SIT')

        (sih,self.system_index_head) = sih.split(',')
        (sit,self.system_index_tail) = sit.split(',')

        sys_index = self.system_index_head

        while int(sys_index) <> -1:
            s=System(self,sys_index)
            s.get_data()
            self.systems[sys_index]=s
            sys_index=s.fwd_index

        res = self.raw('QSL')

        (qsl,p0,p1,p2,p3,p4,p5,p6,p7,p8,p9) = res.split(',')

        l=[tuple(p0),tuple(p1),tuple(p2),tuple(p3),
           tuple(p4),tuple(p5),tuple(p6),tuple(p7),
           tuple(p8),tuple(p9)]

        self.quick_lockout=tuple(map(zero_to_head,l))

        if not self.exit_program_mode(): return 0

        return 1

    def set_scan_settings(self):
        """
        Enters program mode and sets scan settigns to scanner recursively.
        """
        if not self.program_mode:
            self.enter_program_mode()

        l=list(self.quick_lockout)
        l=(map(zero_to_tail,l))
        l=[''.join(t) for t in l]
        pages=','.join(l)
        cmd=','.join(['QSL',pages])

        res = self.raw(cmd)

        for system in self.systems.values():
            system.set_data()

        if not self.exit_program_mode():
            return 0

        return 1

    def dump_system_settings(self):
        """Returns YAML formatted text of scanner settings."""
        return yaml.dump(self.settings.dump())

    def load_system_settings(self,fname):
        """Load YAML formatted text to memory.
        It is up to user to set data into scanner.
        See sample YAML file in examples."""
        settings=yaml.load(file(fname, 'r'))
        self.settings.load(**settings)

    def dump_scan_settings(self):
        """Returns YAML formatted text of scanner scan settings."""
        systems=[]
        for i in self.systems:
            systems.append(self.systems[i].dump())
        s=yaml.dump(systems)
        return s

    def load_scan_settings(self,fname):
        """Load YAML formatted text to memory.
        It is up to user to set data into scanner.
        See sample YAML file in examples.
        """
        stream = file(fname, 'r')
        systems=yaml.load(stream)

        for sys in systems:
            sys_type = scanner_sys_type[sys['type']]
            protected = pyuniden.constants.SCANNER_ONOFF[sys['protected']]
            i=self.create_system(sys_type,protected)
            if i==0: continue
            self.systems[i].load(**sys)

    def create_system(self, sys_type='CNV', protect=0):
        """Creates system instance in scanner memory and returns system index."""
        cmd = ','.join(['CSY',sys_type,str(protect)])
        res = self.raw(cmd)

        (csy,sys_index) = res.split(',')
        if sys_index == -1:
            return 0
        s=System(self,sys_index)
        self.systems[sys_index]=s

        return sys_index

    def delete_system(self, sys_index):
        """Deletes system in scanner memory by system index."""
        cmd = ','.join(['DSY',sys_index])
        res = self.raw(cmd)
        self.systems.pop(sys_index)

    def get_search_settings(self):
        """Enters program mode and gets scanner search settings data recursively."""
        if not self.program_mode:
            self.enter_program_mode()
        self.searches.get_data()
        self.exit_program_mode()

    def set_search_settings(self):
        """Enters program mode and gets scanner search settings data recursively."""
        if not self.program_mode:
            self.enter_program_mode()
        self.searches.set_data()
        self.exit_program_mode()

    def dump_search_settings(self):
        """Returns YAML formatted text of scanner settings."""
        return yaml.dump(self.searches.dump())

    def load_search_settings(self, fname):
        """Load YAML formatted text to memory.
        It is up to user to set data into scanner.
        See sample YAML file in examples.
        """
        searches=yaml.load(file(fname, 'r'))
        self.searches.load(**searches)
