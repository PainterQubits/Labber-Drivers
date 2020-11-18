#!/usr/bin/env python
#below there are some checks for "new_style" because Zurich changed their AWG software libraries at some point, and a lot of the code below is only for the updated libraries
from BaseDriver import LabberDriver, Error
import zhinst
import zhinst.utils

import numpy as np
import textwrap
import time

# define API version
ZI_API = 6


class Driver(LabberDriver):
    """ This class implements a Labber driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        # connect, either through name or by autodetecting
        if self.comCfg.address == '<autodetect>': #input from labber in "Communication" section of the driver
            self.daq = zhinst.utils.autoConnect(api_level=ZI_API)
            self.device = zhinst.utils.autoDetect(self.daq)
        else:
            (self.daq, self.device, _) = zhinst.utils.create_api_session(self.comCfg.address, ZI_API, required_devtype='HDAWG', required_err_msg='This driver requires a HDAWG')
        # keep track of node datatypes
        self.daq.setInt('/{}/system/awg/channelgrouping'.format(self.device), 2)
        self._node_datatypes = dict()
        #internal variables to keep track of when AWGs are in use, waveforms are updated, waveform sizes, etc
        self.n_ch = 8
        self.waveform_updated = [False] * (self.n_ch+1) #+1 is for marker waveform
        self.update_sequencer = False
        self.buffer_sizes = [0] * 4
        self.log('Connected', self.device)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            base = '/%s/awgs/0/' % self.device
            self.daq.setInt(base + 'enable', 0)
        except Exception:
            # never return error here
            pass


    def initSetConfig(self):
        """This function is run before setting values in Set Config. It clears the waveforms"""
        # clear waveforms
        for n in range(self.n_ch):
            self.setValue('AWG%d - Waveform' % (n + 1), [])


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of updated waveforms
        if self.isFirstCall(options): #some Labber thing to check if this call to update instruments is the first call to do so; helps to selectively update some things only on the first call
            self.waveform_updated = [False] * (self.n_ch+1) #lets labber know waveforms are not yet updated
            self.update_sequencer = False #lets labber know waveforms are not yet updated
        # update value, necessary since we later use getValue to get config
        quant.setValue(value) #just updates the local value stored in the driver, no instrument communication is performed

        if quant.get_cmd != '':
            # set node parameters
            value = self._set_node_value(quant, value) #updates the quantity value in the instrument itself
        elif quant.name.endswith(' - Waveform'):
            # mark waveform as updated internally
            awg = int(quant.name[3]) - 1 #get the waveform number
            self.waveform_updated[awg] = True #if a waveform channel is set in Labber, this is updated to True to mark that a the waveform has been filled out
        elif quant.name == 'Waveform Marker':
            self.waveform_updated[-1] = True

        # check if sequencer need to be re-compiled
        if (quant.name.find('Enable AWG') >= 0 or
                quant.name.startswith('Run mode') or
                quant.name.startswith('Trig period') or
                quant.name.startswith('Buffer length') or #buffer length comes into play during external triggering
                quant.name.startswith('Marker Channel')):
            self.update_sequencer = True

        # if final call, make sure instrument is synced before returning
        if self.isFinalCall(options):
            if self.update_sequencer:
                self._configure_sequencer()
                # if sequencer is updated, all waveforms must be uploaded (for example, because buffersize may have changed so you need new waveform sizes)
                self.waveform_updated = [True] * (self.n_ch+1)

            if np.any(self.waveform_updated): #if waveforms have been updated before final call, then upload all the updated waveforms
                self._upload_waveforms(self.waveform_updated) #NOTE NOTE NOTE. WAVEFORMS CAN BE RE-UPLOADED WITHOUT CHANGING THE SEQUENCER PROGRAM! IT'S FASTER THIS WAY! BUT ONLY WORKS IF THE SEQUENCER PROGRAM WAS DEFINED WITH A LONG ENOUGH WAVEFORM IN THE FIRST PLACE!
            self.daq.sync()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.get_cmd != '':
            value = self._get_node_value(quant)
        else:
            # for all others, return local value
            value = quant.getValue()
        return value


    def _map_awg_to_channel(self):
        """Create map between AWGs in use and corresponding output channels, since a single AWG core in the instrument may drive multiple channels, and a single channel may be driven by multiple AWG cores"""
        self.awg_in_use = [False] * self.n_ch
        self.awg_to_ch = [[n] for n in range(self.n_ch)]
        for ch in range(self.n_ch):
            on = self.getValue('Ch%d - Enable AWG %d' % (ch + 1, ch + 1))
            if on:
                self.awg_in_use[ch] = True


    def _configure_sequencer(self, group=1, buffer_size=None):
        """Configure sequencer and upload program for given group. Note that the "Zurich recommended" way is to make waveforms of zeros, and then fill them in"""
        # currently only supports one AWG group
        self._map_awg_to_channel()

        # check version of API
        new_style = hasattr(self.daq, 'setVector')
        # proceed depending on run mode
        run_mode = self.getValue('Run mode')
        # in internal trigger mode, make buffer as long as trig interval
        if run_mode == 'Internal trigger':
            trig_period = self.getValue('Trig period')
            sampling_rate = 2.4E9 / (
                2 ** self.getValueIndex('Sampling rate'))
            # timing changed for new API version
            if new_style:
                # new style - large delays: when running the Zurich in continuous mode, you have it running a while loop, with the paly waveforms command inside the loop. It takes the zurich
                # FOUR microseconds to start the next iteration of the loop after the end of the previous iterations. So the effective "trig period" is always going to be at least 4us. SO, if you have a
                #trig period longer than that, you might as well reduce it by 4us when coding it in the Zurich. MOREOVER, the preferred way of controlling the Zurich through the API is to make a waveform of zeros
                #through LabOne, and then send over your actual waveforms you defined in your Python session. It turns out that changing the awg program through LabOne is time consuming, but replacing this waveform
                # of zeros with other waveforms defined through Python isn't as time-consuming. Thus, if you know your waveforms won't go over a certain size (which you need to be the case in order to have a trigs
                #period defined), it makes sense to make this waveform of zeros as large as you need for your longest waveform, and replace the actual waveform values through the API, rather than wholesale
                #changing the size of the waveforms through LabOne which would be way slower. And since the largest waveform size won't be bigger than the trig period, it makes sense to make the waveform of zeros
                #be the trig period minus 4us. The size of waveform of zeros is called "buffer_size" because that was just Simon's choice; there is NO manipulation of buffers in RAM going on

                buffer_size = int(round((trig_period - 4E-6) * sampling_rate))
                awg_program = textwrap.dedent("""\
                    wave w_marker = marker(_n_, 1);
                    wave w1 = randomUniform(_n_);
                    wave w2 = randomUniform(_n_);
                    wave w3 = randomUniform(_n_);
                    wave w4 = randomUniform(_n_);
                    wave w5 = randomUniform(_n_);
                    wave w6 = randomUniform(_n_);
                    wave w7 = randomUniform(_n_);
                    wave w8 = randomUniform(_n_);
                    setUserReg(0, 0);
                    while(true){
                        while(getUserReg(0) == 0){
                            playWave(1, w1, 2, w2, 3, w3, 4, w4, 5, w5, 6, w6, 7, w7, 8, w8);
                        }
                    }""")  #preferred method of running AWG according to Zurich is to run such a while loop
                    #and to make a waveform of zeros, and then uplaod the actual desired waveforms in their place (wth the length being the same)

            # limit to max memory of unit
            buffer_size = min(buffer_size, 64E6)
            awg_program = awg_program.replace('_n_', ('%d' % buffer_size))

        elif run_mode == 'External trigger':
            buffer_length = self.getValue('Buffer length') #this will be longer than the longest wavefom, but shorter than the trig period. Right now the minimal re-arm time of the instrument with external triggering is unknown
            sampling_rate = 2.4E9 / (
                2 ** self.getValueIndex('Sampling rate'))
            buffer_size = int(round(buffer_length * sampling_rate))
            # limit to max memory of unit
            buffer_size = min(buffer_size, 64E6)

            awg_program = textwrap.dedent("""\
                wave w_marker = marker(_n_, 1);
                wave w1 = randomUniform(_n_);
                wave w2 = randomUniform(_n_);
                wave w3 = randomUniform(_n_);
                wave w4 = randomUniform(_n_);
                wave w5 = randomUniform(_n_);
                wave w6 = randomUniform(_n_);
                wave w7 = randomUniform(_n_);
                wave w8 = randomUniform(_n_);
                setUserReg(0, 0);
                while(true){
                    waitDigTrigger(1);
                    playWave(1, w1, 2, w2, 3, w3, 4, w4, 5, w5, 6, w6, 7, w7, 8, w8);
                }""")
            # the code below trigs faster, but only works for <400 ns waveforms
            # setUserReg(0, 0);
            # while(true){
            #     playWaveDigTrigger(1, %s);

            awg_program = awg_program.replace('_n_', ('%d' % buffer_size))

        #make one of the "waveform of zeros" defined in the awg_program ALSO have a marker waveform, depending on what 'Marker Channel' is
        awg_program_before_marker_split = awg_program.split(';')
        marker_ch = int(self.getValue('Marker Channel')) - 1
        awg_program_before_marker_split[marker_ch + 1] = awg_program_before_marker_split[marker_ch + 1] + ' + w_marker' if marker_ch >= 0 else awg_program_before_marker_split[marker_ch + 1]
        awg_program = ';'.join(awg_program_before_marker_split)

        # keep track of buffer size
        self.buffer_sizes[group - 1] = buffer_size
        # stop current AWG
        base = '/%s/awgs/0/' % self.device
        self.daq.setInt(base + 'enable', 0)
        # compile and upload
        self._upload_awg_program(awg_program)

        # set to single-shot mode and enable
        self.daq.setInt(base + 'single', 1)
        self.daq.setInt(base + 'enable', 1)

    def _upload_waveforms(self, awg_updated=None):
        """Upload all waveforms to device"""
        # check version of API
        new_style = hasattr(self.daq, 'setVector')
        # get updated channels
        if awg_updated is None:
            awg_updated = [True] * self.n_ch

        marker_ch = int(self.getValue('Marker Channel')) - 1; #new addition VF
        marker_ch_core = divmod(marker_ch, 2)[1]
        base = '/%s/triggers/out/' % self.device
        self.daq.setInt(base + str(marker_ch) + '/source', 4 + 2*marker_ch_core) #Zurich commmand to route marker waveform to marker output; 4 corresponds to "Output x Marker 1", 6 corresponds to Output (x+1) Marker 1

        # upload waveforms pairwise, since there are two channels per core
        for ch in range(0, self.n_ch, 2): #checking for the channels in use in pairs, because pairs of channels receive output from same AWG core
            # upload if one or both waveforms are updated per a given core
            if awg_updated[ch] or awg_updated[ch + 1] or ch == marker_ch or ch + 1 == marker_ch:
                # get waveform data
                if self.awg_in_use[ch]:
                    x1 = self.getValueArray('AWG%d - Waveform' % (ch + 1))
                else:
                    # upload a small empty waveform
                    x1 = np.zeros(100)
                if self.awg_in_use[ch + 1]:
                    x2 = self.getValueArray('AWG%d - Waveform' % (ch + 2))
                else:
                    # upload a small empty waveform
                    x2 = np.zeros(100)

                # upload interleaved data
                (core, ch_core) = divmod(ch, 2) #matching up channels to core number, and if it's "channel 0" or "channel 1" in a particular core
                if new_style:
                    # in the new style, waveform must match buffer size
                    n = self.buffer_sizes[0]
                    data = np.zeros((n, 2))
                    data[:len(x1), 0] = x1
                    data[:len(x2), 1] = x2
                    base = '/%s/awgs/%d/' % (self.device, core) #setting up proper command to send to awg

                    if ch == marker_ch or ch + 1 == marker_ch: #makes appropriate marker waveform and uploads all waveforms
                        marker = np.zeros(n)
                        marker_wav = self.getValueArray('Waveform Marker')
                        marker[:len(marker_wav)] = (marker_wav > 0).astype(int) << marker_ch_core*2
                        data_zh = zhinst.utils.convert_awg_waveform(data[:, 0], wave2 = data[:, 1], markers = marker) #zurich function to convert array of wave1, wave2, and markers to their special format
                    else:
                        data_zh = zhinst.utils.convert_awg_waveform(data[:, 0], wave2 = data[:, 1])
                    self.daq.setVector(base + 'waveform/waves/0', data_zh)

                # set enabled
                self.daq.setInt(base + 'enable', 1)


    ################################################# helper functions below

    def _upload_awg_program(self, awg_program, core=0):
        # Transfer the AWG sequence program. Compilation starts automatically.
        # Create an instance of the AWG Module
        awgModule = self.daq.awgModule()
        awgModule.set('awgModule/device', self.device)
        awgModule.set('awgModule/index', int(core))
        awgModule.execute()
        awgModule.set('awgModule/compiler/sourcestring', awg_program)
        while awgModule.getInt('awgModule/compiler/status') == -1:
            time.sleep(0.1)
            if self.isStopped():
                return

        if awgModule.getInt('awgModule/compiler/status') == 1:
            # compilation failed, raise an exception
            raise Error(
                'Upload failed:\n' +
                awgModule.getString('awgModule/compiler/statusstring'))

        if awgModule.getInt('awgModule/compiler/status') == 2:
            self.log(
                "Compiler warning: ",
                awgModule.getString('awgModule/compiler/statusstring'))

        # Wait for the waveform upload to finish
        time.sleep(0.1)
        while ((awgModule.getDouble('awgModule/progress') < 1.0) and
                (awgModule.getInt('awgModule/elf/status') != 1)):
            time.sleep(0.1)
            if self.isStopped():
                return

        if awgModule.getInt('awgModule/elf/status') == 1:
            raise Error("Uploading the AWG program failed.")


    def _get_node_value(self, quant):
        """Get instrument value using ZI node hierarchy"""
        # get node definition
        node = self._get_node(quant)
        dtype = self._get_node_datatype(node)
        # read data from ZI
        d = self.daq.get(node, True)
        if len(d) == 0:
            raise Error('No value defined at node %s.' % node)
        # extract and return data
        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, dict) and 'value' in data:
            data = data['value']
        value = dtype(data[0])

        # convert to index for combo datatypes
        if quant.datatype == quant.COMBO:
            # if no command options are given, use index
            if len(quant.cmd_def) == 0:
                cmd_options = list(range(len(quant.combo_defs)))
            else:
                # convert option list to correct datatype
                cmd_options = [dtype(x) for x in quant.cmd_def]

            # look for correct option
            try:
                index = cmd_options.index(value)
                value = quant.combo_defs[index]
            except Exception:
                raise Error(
                    'Invalid value %s for quantity %s, should be one of %s.' %
                    (str(value), quant.name, str(cmd_options)))

        self.log('Get value', quant.name, node, data, value)
        return value


    def _set_node_value(self, quant, value): #basically just pulling what value to send to the instrument from the .ini file
        #i.e., the options you see in the Labber driver are not exactly what gets sent to the instrument; there is a mapping in the .ini file
        """Set value of quantity using ZI node hierarchy"""
        # get node definition and datatype
        node = self._get_node(quant)
        dtype = self._get_node_datatype(node)

        # special case for combo box items
        if quant.datatype == quant.COMBO:
            index = quant.getValueIndex(value)
            # if no command items are given, send index
            if len(quant.cmd_def) == 0:
                self._set_parameter(node, index)
            # if command options are given, check data type
            else:
                str_value = quant.cmd_def[index]
                self._set_parameter(node, dtype(str_value))

        # standard datatype, just send to instruments
        else:
            self._set_parameter(node, dtype(value))

        # read actual value set by the instrument
        # value = self._get_node_value(quant)
        return value


    def _set_parameter(self, node, value):
        """Set value for given node"""
        if isinstance(value, float):
            # self.daq.setDouble(node, value)
            self.daq.asyncSetDouble(node, value)
        elif isinstance(value, int):
            # self.daq.setInt(node, value)
            self.daq.asyncSetInt(node, value)
        elif isinstance(value, str):
            # self.daq.setString(node, value)
            self.daq.asyncSetString(node, value)
        elif isinstance(value, complex):
            self.daq.setComplex(node, value)


    def _get_node(self, quant):
        """Get node string for quantity"""
        return '/' + self.device + quant.get_cmd


    def _get_node_datatype(self, node):
        """Get datatype for object at node"""
        # used cached value, if available
        if node in self._node_datatypes:
            return self._node_datatypes[node]
        # find datatype from returned data
        d = self.daq.get(node, True)
        if len(d) == 0:
            raise Error('No value defined at node %s.' % node)

        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, dict) and 'value' in data:
            data = data['value']
        # get first item, if python list assume string
        if isinstance(data, list):
            dtype = str
        # not string, should be np array, check dtype
        elif data.dtype in (int, np.int_, np.int64, np.int32, np.int16):
            dtype = int
        elif data.dtype in (float, np.float_, np.float64, np.float32):
            dtype = float
        elif data.dtype in (complex, np.complex_, np.complex64, np.complex128):
            dtype = complex
        else:
            raise Error('Undefined datatype for node %s.' % node)

        # keep track of datatype for future use
        self._node_datatypes[node] = dtype
        self.log('Datatype:', node, dtype)
        return dtype

if __name__ == '__main__':
    pass
