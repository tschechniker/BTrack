"""Build the btrack extension module."""
import os
import os.path
from cffi import FFI


try:
    btrack_root = os.environ['BTRACK_SRC']
except KeyError:
    btrack_root = '../../src'


ffibuilder = FFI()
ffibuilder.cdef("""


typedef struct {
    volatile float bpm;
    volatile float vol;
    ...;
} Context;

const char *get_last_error();

Context *track_beats();

int stop_tracking(Context *ctx);

int has_beats(Context *ctx);

""")


ffibuilder.set_source("_btrack",
r"""
#include <portaudio.h>
#include <thread>
#include <atomic>
#include <cstdint>
#include <math.h>
#include "OnsetDetectionFunction.h"
#include "BTrack.h"

#define SAMPLE_RATE (44100)
#define HOP_SIZE (512)
#define FRAME_SIZE (1024)


thread_local const char *btrack_err = NULL;

int pa_check_error(PaError err) {
    if (err != paNoError) {
        btrack_err = Pa_GetErrorText(err);
        return 1;
    } else {
        btrack_err = NULL;
        return 0;
    }
}


typedef struct {
    volatile float bpm;
    volatile float vol;
    std::atomic_int has_beats;
    PaStream *stream;
} Context;


class PaData {
    BTrack btrack;
    Context *ctx;
    double frame[FRAME_SIZE];
    uint64_t hops;
    uint64_t last_beat_hop;

    public:

    PaData(Context *ctx) : btrack(HOP_SIZE, FRAME_SIZE) {
        this->ctx = ctx;
        hops = 0;
        last_beat_hop = 0;
    }

    void add_hop(const float *inputBuffer, unsigned int samples) {
        assert(HOP_SIZE <= samples);

        unsigned int i = 0;
        for (; i < (FRAME_SIZE - HOP_SIZE); i++ ) {
            frame[i] = frame[i + HOP_SIZE];
        }
        for (; i < FRAME_SIZE; i++) {
            frame[i] = (double) inputBuffer[i - (FRAME_SIZE - HOP_SIZE)];
        }

        float acc = 0.0f;
        for (i = 0; i < FRAME_SIZE; i++) {
            acc += frame[i] * frame[i];
        }
        ctx->vol = sqrt(acc / FRAME_SIZE);

        btrack.processAudioFrame(frame);
        if (btrack.beatDueInCurrentFrame())
        {
            ctx->has_beats++;
            ctx->bpm = (60.0f * SAMPLE_RATE / HOP_SIZE) / (hops - last_beat_hop);
            last_beat_hop = hops;
        }
        hops++;
    }
};


int has_beats(Context *ctx) {
    int beats = ctx->has_beats.load();
    ctx->has_beats -= beats;
    return beats;
}


static int
btrack_on_data(
        const void *inputBuffer,
        void *outputBuffer,
        unsigned long framesPerBuffer,
        const PaStreamCallbackTimeInfo* timeInfo,
        PaStreamCallbackFlags statusFlags,
        void *userData) {

    PaData *data = (PaData *) userData;
    (void) outputBuffer;

    float *inputSamples = (float *)inputBuffer;

    data->add_hop(inputSamples, framesPerBuffer);

    return 0;
}

extern "C" {

const char *get_last_error() {
    return btrack_err;
}

int stop_tracking(Context *ctx) {
    PaError err;

    Pa_AbortStream(ctx->stream);

    err = Pa_CloseStream(ctx->stream);
    if (pa_check_error(err)) {
        return 1;
    }

    return 0;
}


Context *track_beats() {

    Context *ctx = new Context;
    PaData *data = new PaData(ctx);
    PaError err;
    PaStream *stream;

    err = Pa_Initialize();
    if (pa_check_error(err))
        goto error;

    /* Open an audio I/O stream. */
    err = Pa_OpenDefaultStream(
        &stream,
        1,          /* Receive 1 input audio channel */
        0,          /* No output (2 = stereo) */
        paFloat32,  /* 32 bit floating point output */
        SAMPLE_RATE,
        HOP_SIZE,      /* frames per buffer, i.e. the number
                       of sample frames that PortAudio will
                       request from the callback. Many apps
                       may want to use
                       paFramesPerBufferUnspecified, which
                       tells PortAudio to pick the best,
                       possibly changing, buffer size.*/
        btrack_on_data, /* this is your callback function */
        data /* This is a pointer that will be passed to your callback*/
    );
    if (pa_check_error(err))
        goto error;

    ctx->stream = stream;
    err = Pa_StartStream(stream);
    if (pa_check_error(err)) {
        stop_tracking(ctx);
        goto error;
    }

    return ctx;

error:
    err = Pa_Terminate();
    return NULL;
}

}
""",
    source_extension=".cpp",
    sources=[
        os.path.join(btrack_root, 'BTrack.cpp'),
        os.path.join(btrack_root, 'OnsetDetectionFunction.cpp'),
    ],
    libraries=['portaudio', 'fftw3', 'samplerate'],
    include_dirs=[
        btrack_root,
    ],
    extra_compile_args=['-std=c++11'],
    define_macros=[
        ('USE_FFTW', '1'),
    ]
)    # on Unix, link with the math library

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
