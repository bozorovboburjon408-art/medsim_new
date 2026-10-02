import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * useSpeechRecording — Audio yozish va Brauzer Web Speech Recognition (O'zbek tili)
 */
export function useSpeechRecording() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const recognitionRef = useRef(null);
  const chunksRef = useRef([]);
  const transcriptRef = useRef('');

  // Web Speech Recognition ni sozlash
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'uz-UZ'; // O'zbek tili

      recognition.onresult = (event) => {
        let currentText = '';
        for (let i = 0; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript + ' ';
        }
        const trimmed = currentText.trim();
        transcriptRef.current = trimmed;
        setTranscript(trimmed);
      };

      recognition.onerror = (e) => {
        console.warn("Speech recognition ogohlantirish:", e.error);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    setTranscript('');
    transcriptRef.current = '';
    chunksRef.current = [];

    // 1. Speech Recognition ni boshlash
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.debug("Recognition allaqachon faol");
      }
    }

    // 2. MediaRecorder orqali audio oqimini yozish
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: 'audio/webm;codecs=opus' };
      const mimeType = MediaRecorder.isTypeSupported(options.mimeType) ? options.mimeType : '';
      
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const type = mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start(100);
      setIsRecording(true);
    } catch (err) {
      console.error("Mikrofon ruxsati xatosi:", err);
      setError("Mikrofonga ulanib bo'lmadi. Ruxsat berilganini tekshiring.");
    }
  }, []);

  const stopRecording = useCallback(() => {
    // 1. Speech Recognition ni to'xtatish
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }

    // 2. MediaRecorder ni to'xtatish
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  return { isRecording, startRecording, stopRecording, audioBlob, transcript, error };
}
