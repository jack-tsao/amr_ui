"""TTS helper using espeak-ng + aplay.

Encapsulates all speech-related state and subprocess handling that used
to live on :class:`SmartNavNode`. The node holds a :class:`TtsPlayer`
instance and delegates warning / arrival / goodbye / loop speech to it.
"""

import os
import glob
import time
import threading
import subprocess

_ESPEAK_VOICE = "en"


def _synthesize(text: str, output_wav: str, speed: int = 150, pitch: int = 50,
                timeout: float = 5.0, check: bool = False) -> "subprocess.CompletedProcess":
    """Generate a wav file from ``text`` using espeak-ng.

    ``speed`` is words per minute (~80–450, default 175), ``pitch`` is 0–99
    (default 50).
    """
    return subprocess.run(
        [
            "espeak-ng",
            "-v", _ESPEAK_VOICE,
            "-s", str(speed),
            "-p", str(pitch),
            "-w", output_wav,
            text,
        ],
        timeout=timeout,
        check=check,
        capture_output=True,
    )


class TtsPlayer:
    def __init__(self, logger, navigation_state):
        """``navigation_state`` is a callable returning ``(navigation_active, is_avoiding_obstacle)``.

        This lets the warning speech thread decide whether it should
        resume loop speech after finishing, without tightly coupling the
        player back to the node.
        """
        self.logger = logger
        self._navigation_state = navigation_state

        self.keep_speaking = False
        self.speech_thread = None

        self.warning_speech_active = False
        self.warning_speech_thread = None
        self.audio_lock = threading.Lock()
        self.last_warning_time = 0
        self.warning_cooldown = 1.0
        self.normal_speech_paused = False
        self.current_audio_process = None

    # ------------------------------------------------------------------
    # Warning speech
    # ------------------------------------------------------------------
    def play_warning_speech(self):
        def warning_speech():
            try:
                text_to_speak = "Watch out, please keep a little more distance"
                output_wav = f"warning_output_{int(time.time() * 1000) % 10000}.wav"

                _synthesize(text_to_speak, output_wav, speed=140, pitch=70, timeout=5.0)

                if os.path.exists(output_wav):
                    with self.audio_lock:
                        subprocess.run(["aplay", output_wav], timeout=5)
                    self.logger.info("🚨 Playing warning speech: distance too close!")

                    try:
                        os.remove(output_wav)
                    except:
                        pass
                else:
                    self.logger.error("❌ Warning speech file was not generated")

            except subprocess.TimeoutExpired:
                self.logger.error("❌ Warning speech playback timed out")
            except Exception as e:
                self.logger.error(f"❌ Warning speech playback error: {e}")
            finally:
                self.warning_speech_active = False
                navigation_active, is_avoiding_obstacle = self._navigation_state()
                if navigation_active and not is_avoiding_obstacle:
                    self.resume_normal_speech()

        if not self.warning_speech_active:
            self.warning_speech_active = True
            self.warning_speech_thread = threading.Thread(target=warning_speech, daemon=True)
            self.warning_speech_thread.start()

    # ------------------------------------------------------------------
    # Loop speech
    # ------------------------------------------------------------------
    def start_loop_speech(self):
        """Start loop speech playback - lag-fixed version"""
        if self.keep_speaking:
            self.stop_loop_speech()
            time.sleep(0.8)

        self.keep_speaking = True
        self.normal_speech_paused = False

        def speech_loop():
            text_to_speak = "A robot will be passing through shortly. For your safety, please watch your step~"
            consecutive_errors = 0
            max_consecutive_errors = 3

            while self.keep_speaking:
                if self.normal_speech_paused:
                    time.sleep(0.2)
                    consecutive_errors = 0
                    continue

                try:
                    if not self.keep_speaking or self.normal_speech_paused:
                        break

                    output_wav = f"output_{int(time.time() * 1000) % 10000}.wav"

                    process_result = _synthesize(
                        text_to_speak, output_wav, speed=140, pitch=70, timeout=5.0
                    )

                    if process_result.returncode != 0:
                        consecutive_errors += 1
                        self.logger.error(f"espeak-ng failed, return code: {process_result.returncode}")
                        if consecutive_errors >= max_consecutive_errors:
                            self.logger.error("Consecutive speech generation failures, stopping speech playback")
                            break
                        time.sleep(1)
                        continue

                    if not os.path.exists(output_wav):
                        consecutive_errors += 1
                        self.logger.error(f"Speech file {output_wav} was not generated")
                        if consecutive_errors >= max_consecutive_errors:
                            break
                        time.sleep(1)
                        continue

                    if not self.keep_speaking or self.normal_speech_paused:
                        try:
                            os.remove(output_wav)
                        except:
                            pass
                        break

                    with self.audio_lock:
                        if self.keep_speaking and not self.normal_speech_paused:
                            try:
                                self.current_audio_process = subprocess.Popen(
                                    ["aplay", output_wav],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL
                                )

                                start_time = time.time()
                                timeout = 10

                                while self.current_audio_process.poll() is None:
                                    if not self.keep_speaking or self.normal_speech_paused:
                                        self.logger.info("Speech playback interrupted, stopping...")
                                        self.current_audio_process.terminate()
                                        try:
                                            self.current_audio_process.wait(timeout=1)
                                        except subprocess.TimeoutExpired:
                                            self.current_audio_process.kill()
                                        break

                                    if time.time() - start_time > timeout:
                                        self.logger.error(f"Speech playback timed out, force stopping")
                                        self.current_audio_process.terminate()
                                        try:
                                            self.current_audio_process.wait(timeout=1)
                                        except subprocess.TimeoutExpired:
                                            self.current_audio_process.kill()
                                        consecutive_errors += 1
                                        break

                                    time.sleep(0.1)

                                if self.current_audio_process and self.current_audio_process.poll() == 0:
                                    consecutive_errors = 0
                                    self.logger.debug("Speech playback complete")

                            except Exception as e:
                                self.logger.error(f"Error while playing speech: {e}")
                                consecutive_errors += 1
                            finally:
                                self.current_audio_process = None
                                try:
                                    if os.path.exists(output_wav):
                                        os.remove(output_wav)
                                except Exception as e:
                                    self.logger.debug(f"Failed to clean up speech file: {e}")

                    if not self.keep_speaking or self.normal_speech_paused:
                        break

                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error("Too many consecutive playback failures, stopping speech playback")
                        break

                    for i in range(10):
                        if not self.keep_speaking or self.normal_speech_paused:
                            break
                        time.sleep(0.1)

                except subprocess.TimeoutExpired:
                    self.logger.error("espeak-ng process timed out")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                except Exception as e:
                    self.logger.error(f"Speech playback error: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    time.sleep(1)

            self.logger.info("Speech playback thread finished")

        self.speech_thread = threading.Thread(target=speech_loop, daemon=True)
        self.speech_thread.start()
        self.logger.info("🔊 Starting loop speech playback")

    def stop_loop_speech(self):
        """Stop loop speech playback - enhanced version"""
        self.keep_speaking = False
        self.normal_speech_paused = False

        if self.current_audio_process is not None:
            try:
                self.logger.info("Force stopping current audio process...")
                self.current_audio_process.terminate()
                try:
                    self.current_audio_process.wait(timeout=1.0)
                    self.logger.info("Audio process stopped gracefully")
                except subprocess.TimeoutExpired:
                    self.logger.warn("Audio process did not stop gracefully, killing it")
                    self.current_audio_process.kill()
                    try:
                        self.current_audio_process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        self.logger.error("Unable to kill audio process")
            except Exception as e:
                self.logger.error(f"Error while stopping audio process: {e}")
            finally:
                self.current_audio_process = None

        try:
            wav_files = glob.glob("output_*.wav")
            for wav_file in wav_files:
                try:
                    os.remove(wav_file)
                    self.logger.debug(f"Cleaning up speech file: {wav_file}")
                except:
                    pass
        except Exception as e:
            self.logger.debug(f"Error while cleaning up speech files: {e}")

        self.logger.info("🔇 Stopping loop speech playback")

    # ------------------------------------------------------------------
    # Pause / resume normal speech
    # ------------------------------------------------------------------
    def pause_normal_speech(self):
        """Pause normal speech - fixed version"""
        if self.keep_speaking and not self.normal_speech_paused:
            self.normal_speech_paused = True
            self.logger.info("⏸️ Pausing loop speech")

            if self.current_audio_process is not None:
                try:
                    self.current_audio_process.terminate()
                    try:
                        self.current_audio_process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self.current_audio_process.kill()
                    self.logger.info("🛑 Force stopping currently playing normal speech")
                except Exception as e:
                    self.logger.error(f"Error while pausing speech: {e}")
                finally:
                    self.current_audio_process = None

    def resume_normal_speech(self):
        """Resume loop speech"""
        if self.keep_speaking and self.normal_speech_paused:
            self.normal_speech_paused = False
            self.logger.info("▶️ Resuming loop speech")

        if self.speech_thread is None or not self.speech_thread.is_alive():
            self.logger.info("🔧 Speech thread has stopped, restarting")
            self.start_loop_speech()

    # ------------------------------------------------------------------
    # Stop everything
    # ------------------------------------------------------------------
    def stop_all_speech(self):
        """Stop all speech playback - fixed version.

        Returns after clearing internal audio state. The node should
        update its own ``is_avoiding_obstacle`` flag separately since that
        belongs to navigation state.
        """
        self.keep_speaking = False
        self.normal_speech_paused = False

        if self.current_audio_process is not None:
            try:
                self.current_audio_process.terminate()
                try:
                    self.current_audio_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.current_audio_process.kill()
                self.logger.info("🛑 Force stopping currently playing normal speech")
            except Exception as e:
                self.logger.error(f"Error while stopping normal speech: {e}")
            finally:
                self.current_audio_process = None

        self.warning_speech_active = False

        self.logger.info("🔇 All speech playback has been stopped")

    # ------------------------------------------------------------------
    # Arrival / goodbye speech
    # ------------------------------------------------------------------
    def play_arrival_speech(self, returning_home):
        """Play arrival speech - non-blocking fixed version"""
        def arrival_speech():
            try:
                if self.current_audio_process is not None:
                    self.current_audio_process.terminate()
                    self.current_audio_process = None

                if returning_home:
                    text_to_speak = "We have arrived at the final stop, the starting point. Please make sure you have all your belongings. Thank you for using our service today."
                else:
                    text_to_speak = "Your order has been delivered. Please take your item."

                output_wav = "arrival_output.wav"

                _synthesize(text_to_speak, output_wav, speed=155, pitch=30, check=True)

                with self.audio_lock:
                    subprocess.run(["aplay", output_wav], check=True)

            except Exception as e:
                self.logger.error(f"Arrival speech playback error: {e}")

        threading.Thread(target=arrival_speech, daemon=True).start()

    def play_goodbye_speech(self, on_done=None):
        """Play goodbye speech - played at the 20 second mark.

        ``on_done`` is an optional callback invoked in the speech thread's
        ``finally`` block so the node can cancel its goodbye timer.
        """
        def goodbye_speech():
            try:
                text_to_speak = "Thank you. Goodbye."
                output_wav = "goodbye_output.wav"

                _synthesize(text_to_speak, output_wav, speed=155, pitch=60, check=True)

                with self.audio_lock:
                    subprocess.run(["aplay", output_wav], check=True)

                self.logger.info("👋 Playing goodbye speech: Thank you, goodbye")

            except Exception as e:
                self.logger.error(f"Goodbye speech playback error: {e}")
            finally:
                if on_done is not None:
                    try:
                        on_done()
                    except Exception:
                        pass

        threading.Thread(target=goodbye_speech, daemon=True).start()
