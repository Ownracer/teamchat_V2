import React, { useEffect, useRef, useState } from 'react';
import { PhoneOff, Video, Mic } from 'lucide-react';

const VideoCall = ({ roomName, userName, onClose, isVoiceOnly = false }) => {
  const jitsiContainerRef = useRef(null);
  const apiRef = useRef(null);
  const [hasJoined, setHasJoined] = useState(false); // custom pre-join

  const handleStartCall = () => {
    setHasJoined(true); // only then we load Jitsi
  };

  useEffect(() => {
    if (!hasJoined) return; // don’t init Jitsi until user clicks Join

    const domain = 'meet.guifi.net';
    const safeRoomName = roomName.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();

    const options = {
      roomName: safeRoomName,
      width: '100%',
      height: '100%',
      parentNode: jitsiContainerRef.current,
      userInfo: {
        displayName: userName,
      },
      configOverwrite: {
        // ✅ keep Jitsi pre-join OFF (we use our own React pre-join)
        prejoinPageEnabled: false,
        prejoinConfig: { enabled: false },
        disableDeepLinking: true,

        // ❌ DO NOT set startWithAudioMuted / startWithVideoMuted here
      },
      interfaceConfigOverwrite: {
        TOOLBAR_BUTTONS: [
          'microphone',
          'camera',
          'closedcaptions',
          'desktop',
          'fullscreen',
          'fodeviceselection',
          'hangup',
          'profile',
          'chat',
          'recording',
          'livestreaming',
          'etherpad',
          'sharedvideo',
          'settings',
          'raisehand',
          'videoquality',
          'filmstrip',
          'invite',
          'feedback',
          'stats',
          'shortcuts',
          'tileview',
          'videobackgroundblur',
          'download',
          'help',
          'mute-everyone',
          'security',
        ],
      },
    };

    const initJitsi = () => {
      const api = new window.JitsiMeetExternalAPI(domain, options);
      apiRef.current = api;

      // allow iframe to use camera/mic/etc.
      const iframe = api.getIFrame();
      if (iframe) {
        iframe.setAttribute(
          'allow',
          'camera; microphone; display-capture; autoplay; clipboard-write; fullscreen'
        );
      }

      // When user actually joins the conference
      api.addEventListener('videoConferenceJoined', () => {
        console.log('Joined conference');

        // For voice-only rooms: turn video OFF after join
        if (isVoiceOnly) {
          api.executeCommand('toggleVideo'); // if video was on, this turns it off
        }

        // If you want to force mic ON after join, you can do:
        // api.executeCommand('toggleAudio');  // but only if you see it joined muted
      });

      api.addEventListeners({
        videoConferenceLeft: () => onClose(),
        readyToClose: () => onClose(),
        cameraError: (e) => console.error('Jitsi cameraError', e),
        micError: (e) => console.error('Jitsi micError', e),
      });
    };

    if (!window.JitsiMeetExternalAPI) {
      const script = document.createElement('script');
      script.src = 'https://meet.guifi.net/external_api.js';
      script.async = true;
      script.onload = initJitsi;
      document.body.appendChild(script);
    } else {
      initJitsi();
    }

    return () => {
      if (apiRef.current) {
        apiRef.current.dispose();
        apiRef.current = null;
      }
    };
  }, [hasJoined, roomName, userName, isVoiceOnly, onClose]);

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col items-center justify-center">
      {!hasJoined ? (
        // ⭐ Custom pre-join screen (React)
        <div className="bg-white p-8 rounded-xl shadow-2xl flex flex-col items-center max-w-md w-full">
          <div className="w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center mb-6 text-teal-600">
            {isVoiceOnly ? <Mic size={32} /> : <Video size={32} />}
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Ready to join?
          </h2>
          <p className="text-gray-500 mb-8 text-center">
            You are about to join <b>{roomName}</b> as <b>{userName}</b>.
          </p>

          <button
            onClick={handleStartCall}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 px-6 rounded-lg transition-colors shadow-lg flex items-center justify-center space-x-2"
          >
            <span>Join meeting now</span>
          </button>

          <button
            onClick={onClose}
            className="mt-4 text-gray-500 hover:text-gray-800 font-medium"
          >
            Cancel
          </button>
        </div>
      ) : (
        // Jitsi container
        <div className="relative w-full h-full">
          <div ref={jitsiContainerRef} className="w-full h-full" />

          <button
            onClick={onClose}
            className="absolute top-4 right-4 bg-red-600 hover:bg-red-700 text-white p-2 rounded-full shadow-lg z-50 transition-colors"
            title="Close Call Window"
          >
            <PhoneOff size={24} />
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoCall;
