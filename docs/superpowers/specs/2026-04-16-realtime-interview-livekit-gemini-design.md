# Realtime Interview with LiveKit and Gemini Native Audio Design

## Goal

Build the next InterviewX phase as a realtime interview system. HR configures and reviews the interview before publishing it. The system then creates a shareable link for the candidate. When the candidate joins, an AI interviewer joins the same LiveKit room, speaks first, and runs a semi-adaptive interview in Vietnamese or mixed Vietnamese-English.

This phase replaces the earlier text-first interview foundation direction. The target is a real voice and video interview flow built around LiveKit and Gemini native audio.

## Scope

This phase includes:

- HR interview configuration from a completed CV screening
- Three setup modes:
  - generate from AI
  - start blank
  - upload questions
- Full HR control over the final question pack:
  - edit each question
  - reorder questions
  - delete questions
  - add questions
  - add follow-up rules
- Shareable interview link generation
- Candidate join page with LiveKit room access
- Realtime AI interviewer worker that joins the room when the candidate joins
- Gemini 2.5 Flash Native Audio for realtime voice interaction
- Video plus audio call UX, without camera-based analysis
- AI opening the conversation first without waiting for candidate input
- Semi-adaptive interviewing based on the approved question pack
- Transcript persistence
- Post-interview AI summary for HR review

This phase does not include:

- Automatic email delivery of the interview link
- Anti-cheating detection
- Deep interview scorecards
- Final hiring recommendations after the interview
- Scheduler workflows
- Multi-candidate or panel interview rooms
- HR joining the room as a live participant

## Product Decisions Already Chosen

The user has already chosen these requirements.

- Realtime stack: LiveKit plus Gemini 2.5 Flash Native Audio
- Delivery model: Hybrid MVP
- Candidate flow: candidate opens the shareable link, then the AI worker joins the room at the same time
- Session creation: HR creates the interview session and gets a shareable link immediately
- Email sending: not in this phase
- Question control: full custom
- Draft source: HR can generate from AI, start blank, or upload questions
- Runtime behavior: semi-adaptive, not fully freeform
- Candidate experience: video plus audio, but no camera analysis
- Language: default Vietnamese with mixed-mode support
- Post-interview artifacts: transcript plus AI summary

## Why this phase exists

The project brief defines InterviewX as an AI interviewer, not only a CV screener. This phase is the first implementation of that promise.

It also fills the missing operational gap between a completed CV screening and a real interview session. HR needs a way to prepare the interview, approve the questions, publish the session, and let the candidate talk to an AI interviewer in real time.

## Architecture Overview

This design uses three surfaces and two runtime planes.

### 1. Backend API service

The backend is the control plane.

It is responsible for:

- interview configuration
- AI question draft generation
- storing the approved question pack
- publishing the interview session
- generating the shareable link
- minting candidate join credentials
- receiving transcript and summary events from the worker
- serving HR review pages after the call

### 2. Realtime interview worker

The worker is the media and conversation runtime.

It is responsible for:

- joining the LiveKit room as the AI interviewer
- connecting to Gemini native audio live sessions
- sending the opening utterance first
- asking approved questions
- applying bounded follow-up logic
- receiving candidate audio
- streaming transcript and room events back to the backend
- ending the call cleanly
- generating the post-interview summary

### 3. Frontend web app

The frontend exposes two user surfaces.

#### HR surface

- create interview from screening
- choose question source
- configure interview topics and rules
- review, edit, reorder, and publish questions
- copy the shareable link
- review transcript and summary after completion

#### Candidate surface

- open the shareable link
- grant mic and camera permissions
- join the room
- talk to the AI interviewer

## Runtime split

The backend and realtime worker must be separate processes.

The backend should not run the media loop. The worker should not own the main business CRUD flow. This split keeps the backend stable and lets the worker scale independently.

## Recommended stack choice

Use the current Python backend for orchestration and persistence. Add a separate Python realtime worker for LiveKit and Gemini native audio.

This choice fits the current repository best. It also avoids introducing a second main backend runtime before the product proves the flow.

If a later prototype shows that the Node.js LiveKit path is much stronger, the worker can be moved later. This design does not depend on the worker staying in Python forever.

## HR Workflow

### Step 1: Start from a completed screening

HR opens a completed CV screening and clicks Create interview.

### Step 2: Choose the question source

HR chooses one of three modes:

- Generate from AI
- Start blank
- Upload questions

### Step 3: Configure the interview

HR can configure:

- title
- language mode
- target duration
- soft or basic topics
- hard or professional topics
- follow-up intensity
- notes for the AI interviewer

Examples of soft or basic topics:

- short company introduction
- benefits overview
- school schedule
- work availability
- preferred working hours

Examples of hard or professional topics:

- experience summary
- project depth
- role fit
- technology fit
- work examples

### Step 4: Review the question pack

HR reviews an editable question list. For each question HR can:

- rewrite the text
- change the order
- remove it
- add another question
- mark it required or optional
- set follow-up behavior

### Step 5: Publish the session

When HR clicks Publish interview, the system freezes the approved question pack for that session and generates a shareable candidate link.

### Step 6: Share the link

In this phase the product shows the link for copy and manual sharing. The system does not send email yet.

### Step 7: Review the outcome

After the call, HR can review:

- transcript
- AI summary
- session status
- room metadata needed for debugging or audit

## Candidate Workflow

### Step 1: Open the shareable link

The candidate opens a link shaped like:

`/interviews/join/{share_token}`

### Step 2: Pre-join screen

The page shows:

- interview title
- short instructions
- permission prompts for microphone and camera
- a Join button

### Step 3: Join the room

The candidate joins the LiveKit room.

### Step 4: AI joins and speaks first

The AI worker joins the room, opens the Gemini live session, delivers a short introduction, and asks the first question without waiting for the candidate to speak first.

### Step 5: Interview loop

The candidate answers by voice. The AI asks follow-up questions only within the approved rules.

### Step 6: End state

When the session is complete, the AI closes politely, the room ends, and the backend stores the final transcript and summary.

## Why the AI can speak first

This is a session-driven system, not a request-response chat flow.

The trigger is the room lifecycle event, not a typed user prompt. When the candidate joins the room, the worker can:

1. load the session configuration
2. connect to Gemini live
3. send the opening instruction
4. begin speaking immediately

This is how the AI can ask the first question before the candidate says anything.

## Session and data model

### `interview_templates`

Stores the editable draft or prepared template before publication.

Suggested fields:

- `id`
- `jd_document_id`
- `candidate_screening_id`
- `mode`
  - `ai_generated`
  - `blank`
  - `uploaded`
- `language_mode`
  - `vi`
  - `mixed`
- `interview_focus_payload`
- `question_pack_payload`
- `status`
  - `draft`
  - `ready`
- `created_at`
- `updated_at`

### `interview_sessions`

Stores the published session used by the candidate.

Suggested fields:

- `id`
- `candidate_screening_id`
- `interview_template_id`
- `status`
  - `draft`
  - `published`
  - `waiting_for_candidate`
  - `in_progress`
  - `completed`
  - `failed`
- `share_token`
- `livekit_room_name`
- `worker_status`
  - `idle`
  - `dispatching`
  - `joined`
  - `finished`
  - `failed`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`

### `interview_turns`

Stores transcript turns.

Suggested fields:

- `id`
- `interview_session_id`
- `speaker`
  - `agent`
  - `candidate`
  - `system`
- `sequence_number`
- `question_id`
- `transcript_text`
- `language`
- `event_payload`
- `created_at`

### `interview_summaries`

Stores the final AI summary.

Suggested fields:

- `id`
- `interview_session_id`
- `summary_payload`
- `model_name`
- `created_at`

## Question pack contract

Each question should store:

- `id`
- `category`
  - `company_intro`
  - `availability`
  - `motivation`
  - `experience`
  - `technical`
  - `behavioral`
- `prompt`
- `language`
- `priority`
- `ask_style`
  - `required`
  - `optional`
- `follow_up_rule`
- `stop_conditions`
- `notes_for_agent`

## Semi-adaptive rule set

The AI worker must stay inside three layers of control.

### Layer 1: Approved script

The worker must use the approved core question list.

### Layer 2: Follow-up policy

The session config may allow:

- `off`
- `light`
- `normal`

### Layer 3: Per-question rule

Each question may define constraints such as:

- maximum follow-up count
- follow up only if the candidate claims relevant experience
- never follow up on availability questions

The worker must not invent new interview objectives or redirect the session into a new domain that HR did not approve.

## Realtime worker lifecycle

### State 1: Idle

The worker is online and available.

### State 2: Session published

The backend has already created the session, room metadata, and candidate link.

### State 3: Candidate joins the room

The candidate joins the room. This event dispatches or triggers the worker.

### State 4: Worker bootstraps the call

The worker loads:

- session metadata
- approved question pack
- follow-up rules
- language mode
- compact candidate and screening context

Then it connects to Gemini native audio.

### State 5: Opening utterance

The worker sends the first system instruction so the AI greets the candidate and asks the first question.

### State 6: Interview loop

The worker repeats this cycle:

1. receive candidate audio
2. receive model transcript and audio output
3. decide whether to follow up or move to the next approved question
4. persist turns and events

### State 7: Finish

The worker ends the session when one of these happens:

- all required questions are done
- the target duration is reached
- the candidate leaves early
- a fatal runtime error occurs

### State 8: Cleanup

The worker closes the Gemini session, finalizes persistence, and releases runtime resources.

## Candidate link and room flow

### Publish time

The backend creates:

- the interview session row
- the share token
- the LiveKit room name

### Join time

The candidate join page exchanges the share token for:

- candidate room token
- room metadata
- minimal session metadata for the UI

After the candidate joins, the worker is dispatched into the same room.

## Transcript and summary behavior

The worker should stream transcript turns to the backend during the interview. The product should not wait until the very end to persist everything.

At the end of the interview, the worker should generate a concise AI summary for HR. This summary should focus on:

- key topics discussed
- work availability or scheduling notes
- major fit signals
- major uncertainty or concern signals

This phase should not attempt to produce a deep evaluator scorecard.

## Failure handling

The system must fail explicitly.

Important failure cases include:

- worker could not join room
- Gemini live session could not open
- candidate disconnects early
- transcript stream fails partially
- summary generation fails

Rules:

- session status must show the real state
- partial transcript must stay available if already captured
- HR must see whether the session failed or completed
- candidate must not be left in a silent broken state

## Security and access

For this phase:

- HR uses the normal authenticated dashboard
- candidate uses a share token link
- share tokens must be hard to guess
- candidate access should be scoped to one interview session only
- the join endpoint must return only the minimum room metadata needed

## Success criteria

This design is successful when:

- HR can create an interview from a completed screening
- HR can generate, edit, reorder, or upload interview questions
- HR can publish the session and get a shareable link
- candidate can open the link and join the call
- the AI interviewer joins the same room and speaks first
- the interview stays within the approved scope while allowing bounded follow-up
- the transcript is persisted
- the final AI summary is persisted

## Scope boundaries

This design intentionally does not include:

- automatic email sending
- anti-cheating or camera analysis
- deep interview scoring
- scheduling after the interview
- human observer controls
- multi-party interview orchestration
