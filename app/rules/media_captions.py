# backend/app/rules/media_captions.py

from bs4 import BeautifulSoup
from typing import List
from ..schemas import Issue, IssueNode, AiSuggestion

def check_media_captions(html_content: str) -> List[Issue]:
    """
    Checks for <video> and <audio> elements that are missing <track> elements
    for captions (WebVTT) or other text tracks.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Find all <video> and <audio> tags
    media_elements = soup.find_all(['video', 'audio'])

    for element in media_elements:
        element_type = element.name # 'video' or 'audio'
        
        # Check if there are any <track> children with kind="captions" or kind="descriptions"
        has_captions_track = False
        has_descriptions_track = False

        for track in element.find_all('track'):
            kind = track.get('kind')
            if kind == 'captions':
                has_captions_track = True
            elif kind == 'descriptions':
                has_descriptions_track = True
        
        # If it's a video and doesn't have a captions track
        if element_type == 'video' and not has_captions_track:
            issue_html = str(element)
            issues.append(Issue(
                id="custom-video-missing-captions",
                description="Video element is missing a captions track.",
                help="Video content should have synchronized captions (WebVTT) to make it accessible to users who are deaf or hard of hearing, and in situations where audio is unavailable.",
                severity="critical",
                nodes=[IssueNode(html=issue_html, target=["video"])],
                ai_suggestions=AiSuggestion(
                    short_fix="Add a `<track kind=\"captions\" src=\"captions.vtt\" srclang=\"en\" label=\"English\">` element as a child of the `<video>` tag.",
                    detailed_fix=f"Add a `<track>` element with `kind=\"captions\"` as a child of the `<video>` element: `{issue_html}`. The `src` attribute should point to a WebVTT file (.vtt) containing the captions. Include `srclang` (source language, e.g., 'en') and `label` (human-readable track title, e.g., 'English Captions'). Example: `<video controls><source src=\"video.mp4\" type=\"video/mp4\"><track kind=\"captions\" src=\"captions_en.vtt\" srclang=\"en\" label=\"English\"></video>`. Ensure the captions accurately represent all spoken content and important non-speech audio information."
                )
            ))
        
        # If it's an audio and doesn't have a captions track (often used for transcripts in audio)
        # Or if it's a video and doesn't have a descriptions track (for visual content for blind users)
        if element_type == 'audio' and not has_captions_track: # Captions/transcripts for audio
            issue_html = str(element)
            issues.append(Issue(
                id="custom-audio-missing-transcript",
                description="Audio element is missing a captions/transcript track.",
                help="Audio content should have synchronized captions or a transcript provided via a `<track kind=\"captions\">` element to make it accessible to users who are deaf or hard of hearing.",
                severity="critical",
                nodes=[IssueNode(html=issue_html, target=["audio"])],
                ai_suggestions=AiSuggestion(
                    short_fix="Add a `<track kind=\"captions\" src=\"transcript.vtt\" srclang=\"en\" label=\"Transcript\">` element as a child of the `<audio>` tag.",
                    detailed_fix=f"Add a `<track>` element with `kind=\"captions\"` (or `kind=\"subtitles\"` depending on use case) as a child of the `<audio>` element: `{issue_html}`. The `src` attribute should point to a WebVTT file (.vtt) containing the transcript or captions. Include `srclang` (source language, e.g., 'en') and `label` (human-readable track title, e.g., 'Audio Transcript'). Example: `<audio controls><source src=\"audio.mp3\" type=\"audio/mp3\"><track kind=\"captions\" src=\"audio_transcript.vtt\" srclang=\"en\" label=\"Transcript\"></audio>`. Ensure the transcript accurately represents all spoken content."
                )
            ))
        
        if element_type == 'video' and not has_descriptions_track: # Descriptions for video for blind users
            # This is a good practice, but not always a hard WCAG failure at AA level depending on context
            issues.append(Issue(
                id="custom-video-missing-descriptions",
                description="Video element is missing an audio descriptions track.",
                help="Video content, especially with significant visual information not conveyed by audio, should provide audio descriptions via a `<track kind=\"descriptions\">` element for users who are blind or have low vision.",
                severity="moderate", # Marking as moderate as it's often a best practice beyond basic captions
                nodes=[IssueNode(html=str(element), target=["video"])],
                ai_suggestions=AiSuggestion(
                    short_fix="Add a `<track kind=\"descriptions\" src=\"descriptions.vtt\" srclang=\"en\" label=\"Audio Description\">` element as a child of the `<video>` tag.",
                    detailed_fix=f"Consider adding a `<track>` element with `kind=\"descriptions\"` as a child of the `<video>` element: `{issue_html}`. This track should point to a WebVTT file containing audio descriptions for visual content not conveyed by the main audio track. This is particularly important for videos where critical information is presented visually. Example: `<video controls><source src=\"video.mp4\" type=\"video/mp4\"><track kind=\"descriptions\" src=\"video_desc.vtt\" srclang=\"en\" label=\"Audio Description\"></video>`. Ensure descriptions are concise and provide necessary visual information."
                )
            ))
    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/media_captions.py locally ---")

    # Test 1: Video with no tracks (bad)
    html_video_no_tracks = """
    <html><body>
        <video controls src="movie.mp4"></video>
    </body></html>
    """
    issues_video_no_tracks = check_media_captions(html_video_no_tracks)
    print(f"\nTest 1 (Video No Tracks): Found {len(issues_video_no_tracks)} issues.")
    for issue in issues_video_no_tracks:
        print(issue.json(indent=2))

    # Test 2: Audio with no tracks (bad)
    html_audio_no_tracks = """
    <html><body>
        <audio controls src="audio.mp3"></audio>
    </body></html>
    """
    issues_audio_no_tracks = check_media_captions(html_audio_no_tracks)
    print(f"\nTest 2 (Audio No Tracks): Found {len(issues_audio_no_tracks)} issues.")
    for issue in issues_audio_no_tracks:
        print(issue.json(indent=2))

    # Test 3: Video with captions (good for captions, still missing descriptions)
    html_video_with_captions = """
    <html><body>
        <video controls src="movie.mp4">
            <track kind="captions" src="captions.vtt" srclang="en" label="English">
        </video>
    </body></html>
    """
    issues_video_with_captions = check_media_captions(html_video_with_captions)
    print(f"\nTest 3 (Video With Captions): Found {len(issues_video_with_captions)} issues.")
    for issue in issues_video_with_captions:
        print(issue.json(indent=2))

    # Test 4: Video with captions AND descriptions (good)
    html_video_full_tracks = """
    <html><body>
        <video controls src="movie.mp4">
            <track kind="captions" src="captions.vtt" srclang="en" label="English">
            <track kind="descriptions" src="descriptions.vtt" srclang="en" label="Audio Description">
        </video>
    </body></html>
    """
    issues_video_full_tracks = check_media_captions(html_video_full_tracks)
    print(f"\nTest 4 (Video Full Tracks): Found {len(issues_video_full_tracks)} issues.")
    for issue in issues_video_full_tracks:
        print(issue.json(indent=2))
    
    # Test 5: Audio with transcript (good)
    html_audio_with_transcript = """
    <html><body>
        <audio controls src="audio.mp3">
            <track kind="captions" src="transcript.vtt" srclang="en" label="Transcript">
        </audio>
    </body></html>
    """
    issues_audio_with_transcript = check_media_captions(html_audio_with_transcript)
    print(f"\nTest 5 (Audio With Transcript): Found {len(issues_audio_with_transcript)} issues.")
    for issue in issues_audio_with_transcript:
        print(issue.json(indent=2))
