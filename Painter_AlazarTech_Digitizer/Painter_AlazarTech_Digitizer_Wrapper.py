import ctypes, os
from ctypes import c_int, c_uint8, c_uint16, c_uint32, c_int32, c_float, c_char_p, c_void_p, c_long, byref, windll
import numpy as np

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')
import time

# define constants
ADMA_NPT = 0x200
ADMA_EXTERNAL_STARTCAPTURE = 0x1

# match naming convertinos in DLL
U8 = c_uint8
U16 = c_uint16
U32 = c_uint32

class DMABuffer:
    """"Buffer for DMA"""
    def __init__(self, c_sample_type, size_bytes):
        self.size_bytes = size_bytes

        npSampleType = {
            c_uint8: np.uint8,
            c_uint16: np.uint16,
            c_uint32: np.uint32,
            c_int32: np.int32,
            c_float: np.float32
        }.get(c_sample_type, 0)

        bytes_per_sample = {
            c_uint8:  1,
            c_uint16: 2,
            c_uint32: 4,
            c_int32:  4,
            c_float:  4
        }.get(c_sample_type, 0)

        self.addr = None
        if os.name == 'nt':
            MEM_COMMIT = 0x1000
            PAGE_READWRITE = 0x4
            windll.kernel32.VirtualAlloc.argtypes = [c_void_p, c_long, c_long, c_long]
            windll.kernel32.VirtualAlloc.restype = c_void_p
            self.addr = windll.kernel32.VirtualAlloc(
                0, c_long(size_bytes), MEM_COMMIT, PAGE_READWRITE)
        elif os.name == 'posix':
            libc.valloc.argtypes = [c_long]
            libc.valloc.restype = c_void_p
            self.addr = libc.valloc(size_bytes)
        else:
            raise Exception("Unsupported OS")


        ctypes_array = (c_sample_type *
                        (size_bytes // bytes_per_sample)).from_address(self.addr)
        self.buffer = np.frombuffer(ctypes_array, dtype=npSampleType)
        self.ctypes_buffer = ctypes_array
        pointer, read_only_flag = self.buffer.__array_interface__['data']

    def __exit__(self):
        if os.name == 'nt':
            MEM_RELEASE = 0x8000
            windll.kernel32.VirtualFree.argtypes = [c_void_p, c_long, c_long]
            windll.kernel32.VirtualFree.restype = c_int
            windll.kernel32.VirtualFree(c_void_p(self.addr), 0, MEM_RELEASE);
        elif os.name == 'posix':
            libc.free(self.addr)
        else:
            raise Exception("Unsupported OS")

# error type returned by this class
class Error(Exception):
    pass

class TimeoutError(Error):
    pass

# open dll
try:
    DLL = ctypes.CDLL('ATSApi')
except:
    # if failure, try to open in driver folder
    sPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'atsapi')
    DLL = ctypes.CDLL(os.path.join(sPath, 'ATSApi'))


class AlazarTechDigitizer():
    """Represent the Alazartech digitizer, redefines the dll functions in python"""

    def __init__(self, systemId=1, boardId=1, timeout=10.0):
        """The init case defines a session ID, used to identify the instrument"""
        # range settings; default value of 400mV for 9373;
        #will be overwritten if model is 9870 and AlazarInputControl called
        self.dRange = {1: 0.4, 2: 0.4}
        self.buffers = []
        self.timeout = timeout
        # create a session id
        func = getattr(DLL, 'AlazarNumOfSystems')
        func.restype = U32
        func = getattr(DLL, 'AlazarGetBoardBySystemID')
        func.restype = c_void_p
        handle = func(U32(systemId), U32(boardId))
        if handle is None:
            raise Error('Device with system ID=%d and board ID=%d could not be found.' % (systemId, boardId))
        self.handle = handle
        # get mem and bitsize
        (self.memorySize_samples, self.bitsPerSample) = self.AlazarGetChannelInfo()


    def testLED(self):
        import time
        self.callFunc('AlazarSetLED', self.handle, U32(1))
        time.sleep(0.1)
        self.callFunc('AlazarSetLED', self.handle, U32(0))


    def callFunc(self, sFunc, *args, **kargs):
        """General function caller with restype=status, also checks for errors"""
        # get function from DLL
        func = getattr(DLL, sFunc)
        func.restype = c_int
        # call function, raise error if needed
        status = func(*args)
        if 'bIgnoreError' in kargs:
            bIgnoreError = kargs['bIgnoreError']
        else:
            bIgnoreError = False
        if status>512 and not bIgnoreError:
            sError = self.getError(status)
            raise Error(sError)


    def getError(self, status):
        """Convert the error in status to a string"""
        func = getattr(DLL, 'AlazarErrorToText')
        func.restype = c_char_p
        # const char* AlazarErrorToText(RETURN_CODE retCode)
        errorText = func(c_int(status))
        return str(errorText)



    def AlazarGetChannelInfo(self):
        '''Get the on-board memory in samples per channe and sample size in bits per sample'''
        memorySize_samples = U32(0)
        bitsPerSample = U8(0)
        self.callFunc('AlazarGetChannelInfo', self.handle, byref(memorySize_samples), byref(bitsPerSample))
        return (int(memorySize_samples.value), int(bitsPerSample.value))


    #RETURN_CODE AlazarSetCaptureClock( HANDLE h, U32 Source, U32 Rate, U32 Edge, U32 Decimation);
    def AlazarSetCaptureClock(self, SourceId, SampleRateId, EdgeId=0, Decimation=0):
        self.callFunc('AlazarSetCaptureClock', self.handle,
                      U32(SourceId), U32(SampleRateId), U32(EdgeId), U32(Decimation))


    #RETURN_CODE AlazarInputControl( HANDLE h, U8 Channel, U32 Coupling, U32 InputRange, U32 Impedance);
    def AlazarInputControl(self, Channel, Coupling, InputRange, Impedance):
        # keep track of input range
        dConv = {12: 4.0, 11: 2.0, 10: 1.0, 7: 0.4, 6: 0.2, 5: 0.1, 2: 0.04}
        self.dRange[Channel] = dConv[InputRange]
        self.callFunc('AlazarInputControl', self.handle,
                      U8(Channel), U32(Coupling), U32(InputRange), U32(Impedance))


    #RETURN_CODE AlazarSetBWLimit( HANDLE h, U8 Channel, U32 enable);
    def AlazarSetBWLimit(self, Channel, enable):
        self.callFunc('AlazarSetBWLimit', self.handle, U32(Channel), U32(enable))


    #RETURN_CODE AlazarSetTriggerOperation(HANDLE h, U32 TriggerOperation
    #            ,U32 TriggerEngine1/*j,K*/, U32 Source1, U32 Slope1, U32 Level1
    #            ,U32 TriggerEngine2/*j,K*/, U32 Source2, U32 Slope2, U32 Level2);
    def AlazarSetTriggerOperation(self, TriggerOperation=0,
                                  TriggerEngine1=0, Source1=0, Slope1=1, Level1=128,
                                  TriggerEngine2=1, Source2=3, Slope2=1, Level2=128):
        self.callFunc('AlazarSetTriggerOperation', self.handle, U32(TriggerOperation),
                      U32(TriggerEngine1), U32(Source1), U32(Slope1), U32(Level1),
                      U32(TriggerEngine2), U32(Source2), U32(Slope2), U32(Level2))


    #RETURN_CODE AlazarSetExternalTrigger( HANDLE h, U32 Coupling, U32 Range);
    def AlazarSetExternalTrigger(self, Coupling, Range=0):
        self.callFunc('AlazarSetExternalTrigger', self.handle, U32(Coupling), U32(Range))


    #RETURN_CODE  AlazarSetTriggerDelay( HANDLE h, U32 Delay);
    def AlazarSetTriggerDelay(self, Delay=0):
        self.callFunc('AlazarSetTriggerDelay', self.handle, U32(Delay))


    #RETURN_CODE  AlazarSetTriggerTimeOut( HANDLE h, U32 to_ns);
    def AlazarSetTriggerTimeOut(self, time=0.0):
        tick = U32(int(time*1E5))
        self.callFunc('AlazarSetTriggerTimeOut', self.handle, tick)


    #RETURN_CODE AlazarSetRecordSize( HANDLE h, U32 PreSize, U32 PostSize);
    def AlazarSetRecordSize(self, PreSize, PostSize):
        self.nPreSize = int(PreSize)
        self.nPostSize = int(PostSize)
        self.callFunc('AlazarSetRecordSize', self.handle, U32(PreSize), U32(PostSize))


    #RETURN_CODE AlazarSetRecordCount( HANDLE h, U32 Count);
    def AlazarSetRecordCount(self, Count):
        self.nRecord = int(Count)
        self.callFunc('AlazarSetRecordCount', self.handle, U32(Count))


    #RETURN_CODE AlazarStartCapture( HANDLE h);
    def AlazarStartCapture(self):
        self.callFunc('AlazarStartCapture', self.handle)


    #RETURN_CODE AlazarAbortCapture( HANDLE h);
    def AlazarAbortCapture(self):
        self.callFunc('AlazarAbortCapture', self.handle)


    #U32	AlazarBusy( HANDLE h);
    def AlazarBusy(self):
        # get function from DLL
        func = getattr(DLL, 'AlazarBusy')
        func.restype = U32
        # call function, return result
        return bool(func(self.handle))


    # U32	AlazarRead(HANDLE h, U32 Channel, void *buffer, int ElementSize,
    #                 long Record, long TransferOffset, U32 TransferLength);
    def AlazarRead(self, Channel, buffer, ElementSize, Record, TransferOffset, TransferLength):
        self.callFunc('AlazarRead', self.handle,
                      U32(Channel), buffer, c_int(ElementSize),
                      c_long(Record), c_long(TransferOffset), U32(TransferLength))


    def AlazarBeforeAsyncRead(self, channels, transferOffset, samplesPerRecord,
                        recordsPerBuffer, recordsPerAcquisition, flags):
        '''Prepares the board for an asynchronous acquisition.'''
        self.callFunc('AlazarBeforeAsyncRead', self.handle, channels, transferOffset, samplesPerRecord,
                                  recordsPerBuffer, recordsPerAcquisition, flags)


     #RETURN_CODE AlazarAbortAsyncRead( HANDLE h);
    def AlazarAbortAsyncRead(self):
        '''Cancels any asynchronous acquisition running on a board.'''
        self.callFunc('AlazarAbortAsyncRead', self.handle)


    def AlazarPostAsyncBuffer(self, buffer, bufferLength):
        '''Posts a DMA buffer to a board.'''
        self.callFunc('AlazarPostAsyncBuffer', self.handle, buffer, bufferLength)


    def AlazarWaitAsyncBufferComplete(self, buffer, timeout_ms):
        '''Blocks until the board confirms that buffer is filled with data.'''
        self.callFunc('AlazarWaitAsyncBufferComplete', self.handle, buffer, timeout_ms)


    def readTracesDMA(self, bGetCh1, bGetCh2, nSamples, nRecord, nBuffer, nAverage=1,
                      bConfig=True, bArm=True, bMeasure=True,
                      funcStop=None, funcProgress=None, timeout=None, bufferSize=512,
                      firstTimeout=None, maxBuffers=1024):
        """read traces in NPT AutoDMA mode, convert to float, average to single trace"""
        t0 = time.clock()
        lT = []

        # use global timeout if not given
        timeout = self.timeout if timeout is None else timeout
        # first timeout can be different in case of slow initial arming
        firstTimeout = timeout if firstTimeout is None else firstTimeout

        #Select the number of pre-trigger samples...not supported in NPT, keeping for consistency
        preTriggerSamplesValue = 0
        #change alignment to be 128
        if preTriggerSamplesValue > 0:
            preTriggerSamples = int(np.ceil(preTriggerSamplesValue / 128.)  *128)
        else:
            preTriggerSamples = 0

        #Select the number of samples per record.
        postTriggerSamplesValue = nSamples
        #change alignment to be 128
        postTriggerSamples = int(np.ceil(postTriggerSamplesValue / 128.)*128)
        samplesPerRecordValue = preTriggerSamplesValue + postTriggerSamplesValue

        #Select the number of records per DMA buffer.
        nRecordTotal = nRecord * nAverage
        if nRecord > 1:
            # if multiple records wanted, set records per buffer to match
            recordsPerBuffer = nRecord
        else:
            # else, use 100 records per buffers
            recordsPerBuffer = nBuffer
        buffersPerAcquisition = int(np.ceil(nRecordTotal/float(recordsPerBuffer)))
        if nRecordTotal < recordsPerBuffer:
            recordsPerBuffer = nRecordTotal

        #Select the active channels.
        Channel1 = 1 if bGetCh1 else 0
        Channel2 = 2 if bGetCh2 else 0

        channels = Channel1 | Channel2
        channelCount = 0
        for n in range(16):
            c = int(2**n)
            channelCount += (c & channels == c)

        # return directly if no active channels
        if channelCount == 0:
            return [np.array([], dtype=float), np.array([], dtype=float)]

        # Compute the number of bytes per record and per buffer
        bytesPerSample = (self.bitsPerSample + 7) // 8
        samplesPerRecord = preTriggerSamples + postTriggerSamples
        bytesPerRecord = bytesPerSample * samplesPerRecord
        bytesPerBuffer = bytesPerRecord * recordsPerBuffer * channelCount
        # force buffer size to be integer of 256 * 16 = 4096, not sure why
        bytesPerBufferMem = int(4096 * np.ceil(bytesPerBuffer/4096.))

        recordsPerAcquisition = recordsPerBuffer * buffersPerAcquisition
        # TODO: Select number of DMA buffers to allocate
        MEM_SIZE = int(bufferSize * 1024*1024)
        # force buffer count to be even number, seems faster for allocating
        maxBufferCount = int(MEM_SIZE//(2*bytesPerBufferMem))
        bufferCount = max(1, 2*maxBufferCount)
        # don't allocate more buffers than needed for all data
        bufferCount = min(bufferCount, buffersPerAcquisition, maxBuffers)
        lT.append('Total buffers needed: %d' % buffersPerAcquisition)
        lT.append('Buffer count: %d' % bufferCount)
        lT.append('Buffer size: %d' % bytesPerBuffer)
        lT.append('Buffer size, memory: %d' % bytesPerBufferMem)
        lT.append('Records per buffer: %d' % recordsPerBuffer)

        # configure board, if wanted
        if bConfig:
            self.AlazarSetRecordSize(preTriggerSamples, postTriggerSamples)
            self.AlazarSetRecordCount(recordsPerAcquisition)
            # Allocate DMA buffers
            sample_type = ctypes.c_uint8
            if bytesPerSample > 1:
                sample_type = ctypes.c_uint16
            # clear old buffers
            self.removeBuffersDMA()
            # create new buffers
            self.buffers = []
            for i in range(bufferCount):
                self.buffers.append(DMABuffer(sample_type, bytesPerBufferMem))

        # arm and start capture, if wanted
        if bArm:
            # Configure the board to make a Traditional AutoDMA acquisition
            self.AlazarBeforeAsyncRead(channels,
                                  -preTriggerSamples,
                                  samplesPerRecord,
                                  recordsPerBuffer,
                                  recordsPerAcquisition,
                                  ADMA_EXTERNAL_STARTCAPTURE | ADMA_NPT)
            # Post DMA buffers to board
            for buf in self.buffers:
                self.AlazarPostAsyncBuffer(buf.addr, buf.size_bytes)
            try:
                self.AlazarStartCapture()
            except:
                # make sure buffers release memory if failed
                self.removeBuffersDMA()
                raise

        # if not waiting for result, return here
        if not bMeasure:
            return

        lT.append('Post: %.1f ms' % ((time.clock()-t0)*1000))
        try:
            lT.append('Start: %.1f ms' % ((time.clock()-t0)*1000))
            buffersCompleted = 0
            bytesTransferred = 0
            #initialize data array
            nPtsOut = samplesPerRecord * nRecord
            nAvPerBuffer = recordsPerBuffer/nRecord
            vData = [np.zeros(nPtsOut, dtype=float), np.zeros(nPtsOut, dtype=float)]
            #range and zero for conversion to voltages
            codeZero = 2 ** (float(self.bitsPerSample) - 1) - 0.5
            codeRange = 2 ** (float(self.bitsPerSample) - 1) - 0.5
            # range and zero for each channel, combined with bit shifting
            range1 = self.dRange[1]/codeRange # /16.
            range2 = self.dRange[2]/codeRange #/16.
            offset = 16.*0 + codeZero

            timeout_ms = int(firstTimeout*1000)

            log.info(str(lT))
            lT = []

            while (buffersCompleted < buffersPerAcquisition):
                # Wait for the buffer at the head of the list of available
                # buffers to be filled by the board.
                buf = self.buffers[buffersCompleted % len(self.buffers)]
                self.AlazarWaitAsyncBufferComplete(buf.addr, timeout_ms=timeout_ms)
                # lT.append('Wait: %.1f ms' % ((time.clock()-t0)*1000))

                # reset timeout time, can be different than first call
                timeout_ms = int(timeout*1000)

                buffersCompleted += 1
                bytesTransferred += buf.size_bytes

                # break if stopped from outside
                if funcStop is not None and funcStop():
                    break
                # report progress
                if funcProgress is not None:
                    funcProgress(float(buffersCompleted)/float(buffersPerAcquisition))

                # remove extra elements for getting even 256*16 buffer sizes
                if bytesPerBuffer == bytesPerBufferMem:
                    buf_truncated = buf.buffer
                else:
                    buf_truncated = buf.buffer[:(bytesPerBuffer//bytesPerSample)]

                # reshape, sort and average data
                if nAverage > 1:
                    if channels == 1:
                        rs = buf_truncated.reshape((nAvPerBuffer, nPtsOut))
                        vData[0] += range1 * (np.mean(rs, 0)  - offset)
                    elif channels == 2:
                        rs = buf_truncated.reshape((nAvPerBuffer, nPtsOut))
                        vData[1] += range2 * (np.mean(rs, 0)  - offset)
                    elif channels == 3:
                        rs = buf_truncated.reshape((2, nAvPerBuffer, nPtsOut)) # changed from buf_truncated.reshape((nAvPerBuffer, nPtsOut, 2))
                        vData[0] += range1 * (np.mean(rs[0,:,:], 0)  - offset) # changed from range1 * (np.mean(rs[:,:,0], 0)  - offset)
                        vData[1] += range2 * (np.mean(rs[1,:,:], 0)  - offset) # changed from range1 * (np.mean(rs[:,:,1], 0)  - offset)
                else:
                    if channels == 1:
                        vData[0] = range1 * (buf_truncated  - offset)
                    elif channels == 2:
                        vData[1] = range2 * (buf_truncated  - offset)
                    elif channels == 3:
                        rs = buf_truncated.reshape((2, nPtsOut)) # changed from buf_truncated.reshape((nPtsOut, 2))
                        vData[0] = range1 * (rs[0, :]  - offset) # changed from range1 * (rs[:, 0]  - offset)
                        vData[1] = range2 * (rs[1, :]  - offset) # changed from range1 * (rs[:, 1]  - offset)

                # lT.append('Sort/Avg: %.1f ms' % ((time.clock()-t0)*1000))
                # log.info(str(lT))
                # lT = []
                #
                # Sample codes are unsigned by default. As a result:
                # - 0x00 represents a negative full scale input signal.
                # - 0x80 represents a ~0V signal.
                # - 0xFF represents a positive full scale input signal.

                # Add the buffer to the end of the list of available buffers.
                self.AlazarPostAsyncBuffer(buf.addr, buf.size_bytes)
        finally:
            # release resources
            try:
                self.AlazarAbortAsyncRead()
            except:
                pass
            lT.append('Abort: %.1f ms' % ((time.clock()-t0)*1000))
        # normalize
        # log.info('Average: %.1f ms' % np.mean(lAvTime))
        vData[0] /= buffersPerAcquisition
        vData[1] /= buffersPerAcquisition
        # # log timing information
        lT.append('Done: %.1f ms' % ((time.clock()-t0)*1000))
        log.info(str(lT))
        #return data - requested vector length, not restricted to 128 multiple
        if nPtsOut != (samplesPerRecordValue*nRecord):
            if len(vData[0])>0:
                vData[0] = vData[0].reshape((nRecord,samplesPerRecord))[:,:samplesPerRecordValue].flatten()
            if len(vData[1])>0:
                vData[1] = vData[1].reshape((nRecord,samplesPerRecord))[:,:samplesPerRecordValue].flatten()
        return vData


    def removeBuffersDMA(self):
        """Clear and remove DMA buffers, to release memory"""
        # make sure buffers release memory
        for buf in self.buffers:
            buf.__exit__()
        # remove all
        self.buffers = []


    def readTraces(self, Channel):
        """Read traces, convert to float, average to a single trace"""
        # define sizes
        bitsPerSample = 8
        bytesPerSample = int(np.floor((float(bitsPerSample) + 7.) / 8.0))
        #TODO: change so buffer alignment is 64!!
        samplesPerRecord = self.nPreSize + self.nPostSize
        # The buffer must be at least 16 samples larger than the transfer size
        samplesPerBuffer = samplesPerRecord + 16
        dataBuffer = (c_uint8*samplesPerBuffer)()
        # define scale factors
        codeZero = 2 ** (float(bitsPerSample) - 1) - 0.5
        codeRange = 2 ** (float(bitsPerSample) - 1) - 0.5
        voltScale = self.dRange[Channel] /codeRange
        # initialize a scaled float vector
        vData = np.zeros(samplesPerRecord, dtype=float)
        for n1 in range(self.nRecord):
            self.AlazarRead(Channel, dataBuffer, bytesPerSample, n1+1,
                            -self.nPreSize, samplesPerRecord)
            # convert and scale to float
            vBuffer = voltScale * ((np.array(dataBuffer[:samplesPerRecord]) - codeZero))
            # add to output vector
            vData += vBuffer
        # normalize
        vData /= float(self.nRecord)
        return vData



if __name__ == '__main__':
    #
    # test driver
    Digitizer = AlazarTechDigitizer()