# Đánh giá Agentic AI cho InterviewX

## Mục tiêu tài liệu

Tài liệu này đánh giá InterviewX theo đúng tinh thần chủ đề **"Agentic AI – Agents of Change"** của GDGoC Hackathon 2026, tập trung vào 4 trụ cột:

1. Goal-driven
2. Planning
3. Autonomy
4. Feedback Loop

Mục tiêu không chỉ là chấm xem project có "dùng AI" hay không, mà là xác định:
- phần nào của hệ thống đã thể hiện tính agentic thật sự,
- phần nào mới dừng ở mức workflow automation hoặc AI-enhanced product,
- cần cải tiến gì để thuyết phục giám khảo ở vòng 2 và vòng pitching.

---

## Tóm tắt kết luận

InterviewX **đúng hướng agentic**, nhưng hiện tại mạnh nhất ở **goal-driven workflow** và **system orchestration**, còn yếu hơn ở **planning hiển lộ**, **decision transparency**, và đặc biệt là **feedback loop khép kín**.

### Chấm nhanh theo 4 tiêu chí

| Tiêu chí | Đánh giá | Nhận xét ngắn |
|---|---:|---|
| Goal-driven | 8.5/10 | Có mục tiêu nghiệp vụ rõ, không phải chatbot đơn lẻ |
| Planning | 7.0/10 | Có decomposition nhưng chưa show rõ agent plan/re-plan |
| Autonomy | 7.5/10 | Có autonomy mức hệ thống, chưa đủ mạnh ở decision autonomy |
| Feedback Loop | 5.5/10 | Có data nền tảng nhưng chưa có vòng học hỏi khép kín để demo |

### Kết luận một câu

**InterviewX hiện là một sản phẩm AI workflow rất tốt, đang tiến gần tới agentic system, nhưng cần thêm bằng chứng về plan visibility, adaptive decision-making, và learning loop để đạt mức thuyết phục cao trong chủ đề hackathon.**

---

## Cách đánh giá được sử dụng

Phần đánh giá này kết hợp:
- chủ đề chính thức của hackathon: **Goal-driven, Planning, Autonomy, Feedback Loop**,
- các framework đánh giá agent phổ biến gần đây như:
  - Goal-Plan-Action alignment,
  - decision logging và plan adherence,
  - agent reliability / observability / human-in-the-loop,
  - success-rate + demo checklist cho agentic systems.

### Ý nghĩa thực tế của 4 tiêu chí

#### 1. Goal-driven
Agent không chỉ phản hồi từng input rời rạc, mà theo đuổi một **mục tiêu nghiệp vụ rõ ràng**.

#### 2. Planning
Agent biết **phân tích mục tiêu**, chia nhỏ thành bước con, chọn trình tự thực thi hợp lý, và nếu cần thì điều chỉnh kế hoạch.

#### 3. Autonomy
Agent có thể **tự quyết định hành động tiếp theo** trong phạm vi cho phép, thay vì chỉ chạy flow cố định do code định nghĩa cứng.

#### 4. Feedback Loop
Agent có khả năng **quan sát kết quả**, được phản hồi, rồi **cải thiện chiến lược cho lần sau**.

---

## Bằng chứng hiện có trong codebase

### Goal-driven workflow
InterviewX đang có một pipeline hướng đích khá rõ:
- upload và phân tích JD,
- screen CV,
- sinh câu hỏi phỏng vấn,
- publish interview,
- ứng viên join vào room,
- ghi transcript/runtime events,
- tổng hợp review sau buổi phỏng vấn.

Các điểm thể hiện rõ:
- `backend/src/api/v1/jd.py:65`
- `backend/src/api/v1/interviews.py:37`
- `backend/src/api/v1/interviews.py:49`
- `backend/src/api/v1/interviews.py:117`
- `backend/src/services/jd_service.py:98`

### Planning foundation
Hệ thống đã có dấu hiệu planning ở các bước:
- phân tích JD thành cấu trúc requirements và rubric seed,
- dùng screening context để generate question set,
- cho HR review trước khi publish phiên interview,
- giữ schedule và trạng thái phiên để điều phối flow tiếp theo.

Các điểm thể hiện rõ:
- `backend/src/services/jd_service.py:167`
- `frontend/src/components/interview/interview-launch-panel.tsx:160`
- `frontend/src/components/interview/interview-launch-panel.tsx:222`

### Autonomy foundation
Project đã có autonomy ở mức system orchestration:
- enqueue background jobs thay vì xử lý đồng bộ thủ công,
- lưu runtime event và cập nhật session state theo event,
- cho phép session transition theo trạng thái runtime,
- query company knowledge theo session context.

Các điểm thể hiện rõ:
- `backend/src/services/jd_service.py:98`
- `backend/src/services/interview_runtime_service.py:14`
- `backend/src/api/v1/interviews.py:156`
- `backend/src/api/v1/interviews.py:181`

### Feedback data foundation
Project đã có nền tảng dữ liệu cho feedback loop:
- transcript turns,
- runtime events,
- session review,
- summary payload.

Các điểm thể hiện rõ:
- `backend/src/api/v1/interviews.py:91`
- `backend/src/api/v1/interviews.py:144`
- `backend/src/services/interview_runtime_service.py:43`
- `frontend/src/components/interview/live-room.tsx:285`

---

## Đánh giá chi tiết theo 4 trụ cột

## 1. Goal-driven

### Điểm mạnh
InterviewX không dừng ở kiểu hỏi-đáp hoặc assistant chung chung. Hệ thống theo đuổi một mục tiêu tuyển dụng rất cụ thể:

> Biến JD thành quy trình tuyển dụng bán tự động hoặc tự động một phần, giúp HR chỉ tập trung vào ứng viên đã được AI sàng lọc và phỏng vấn sơ bộ.

Đây là điểm rất mạnh vì nó cho thấy AI không phải là một feature nhỏ, mà là **core execution engine** của product.

### Vì sao đạt điểm cao
- mục tiêu đầu-cuối rõ,
- nhiều bước hành động cùng phục vụ một outcome nghiệp vụ,
- có context continuity giữa JD, screening, interview, review.

### Điểm còn thiếu
Hiện tại goal có tồn tại trong hệ thống, nhưng **chưa được hiển lộ đủ rõ cho người chấm**. Nếu demo chỉ là các page nối nhau, giám khảo có thể nhìn đây là một sản phẩm workflow có gắn AI, thay vì một agent đang theo đuổi goal.

### Cải tiến đề xuất
1. Hiển thị rõ **Agent Goal** trong UI hoặc demo script:
   - ví dụ: "Goal hiện tại: đánh giá mức phù hợp của ứng viên với JD Backend Engineer".
2. Gắn outcome đo được vào goal:
   - shortlisted,
   - confidence score,
   - competency coverage,
   - recommendation.
3. Khi pitch, dùng câu mở đầu dạng:
   - "Agent của chúng tôi không chỉ trả lời, mà theo đuổi mục tiêu tuyển dụng từ JD đến shortlist."

### Đánh giá
**8.5/10**

---

## 2. Planning

### Điểm mạnh
InterviewX đã có cấu trúc gần với planning:
- JD được phân rã thành requirements và rubric,
- manual questions + guidance được biến thành question set,
- HR có bước review trước khi publish,
- interview flow có current question index và plan context hiển thị trong live room.

Điểm đáng chú ý trong UI live room:
- `frontend/src/components/interview/live-room.tsx:287`
- `frontend/src/components/interview/live-room.tsx:312`

Điều này cho thấy hệ thống đã có khái niệm **interview plan** chứ không chỉ sinh ngẫu nhiên từng câu hỏi.

### Điểm yếu cốt lõi
Planning hiện tại vẫn giống:
- "có các bước xử lý trước interview"

nhiều hơn là:
- "agent tự lập kế hoạch và tái lập kế hoạch trong runtime".

Những chỗ còn thiếu:
- chưa có màn hình hoặc artifact thể hiện plan một cách rõ ràng,
- chưa thấy explicit reasoning về việc vì sao câu hỏi A được hỏi trước B,
- chưa thấy re-planning khi ứng viên trả lời tốt/xấu.

### Rủi ro khi bị giám khảo hỏi
Nếu bị hỏi:
> Agent plan ở đâu? Nó có thực sự chia nhỏ mục tiêu và chọn chiến lược không?

thì hiện tại câu trả lời vẫn nghiêng về giải thích kiến trúc hơn là cho thấy proof trực tiếp trong product.

### Cải tiến đề xuất
#### P0
1. Thêm một **Interview Plan Panel** gồm:
   - mục tiêu buổi interview,
   - 4 competency chính,
   - thứ tự ưu tiên,
   - số câu hỏi dự kiến mỗi competency,
   - điều kiện chuyển hướng.
2. Lưu plan snapshot vào session để có thể show lại sau khi publish.
3. Ghi rõ câu hỏi nào đến từ:
   - manual,
   - JD rubric,
   - adaptive follow-up.

#### P1
4. Khi runtime đổi hướng, ghi event:
   - `plan.adjusted`
   - reason: thiếu bằng chứng về system design / candidate trả lời quá generic / cần đào sâu leadership.
5. Thêm phần "Why this next question?" trong live monitoring.

### Đánh giá
**7.0/10**

---

## 3. Autonomy

### Điểm mạnh
Autonomy của InterviewX hiện mạnh ở mức **system action autonomy**:
- tự queue job xử lý nền,
- tự cập nhật session state theo event,
- tự quản lý room/session lifecycle,
- tự truy vấn company knowledge cho interview context.

Điều này chứng minh hệ thống không phải thao tác tay từng bước.

### Điểm yếu cốt lõi
Thứ còn thiếu là **decision autonomy nhìn thấy được**.

Giám khảo sẽ không chỉ hỏi:
- hệ thống có tự chạy không?

mà còn hỏi:
- hệ thống tự quyết định cái gì?
- dựa vào tiêu chí nào?
- khi điều kiện thay đổi, nó tự đổi chiến lược ra sao?

Hiện tại nhiều autonomy của project vẫn nằm ở mức:
- event đến thì cập nhật state,
- request đến thì xử lý flow tương ứng.

Tức là autonomy có, nhưng thiên về orchestration hơn là decision-making.

### Cải tiến đề xuất
#### P0
1. Thêm **Decision Log** cho interview runtime:
   - next action,
   - lý do,
   - evidence,
   - confidence,
   - affected competency.
2. Log rõ adaptive decisions, ví dụ:
   - tăng độ khó,
   - chuyển từ technical sang behavioral,
   - đào sâu câu trả lời cũ,
   - kết thúc vì đã đủ evidence.
3. Phân biệt rõ trong transcript/review:
   - planned question,
   - follow-up question,
   - recovery question,
   - clarification question.

#### P1
4. Thêm autonomy guardrails:
   - chỉ tự advance khi confidence vượt ngưỡng,
   - nếu confidence thấp thì escalate cho HR.
5. Hiển thị "human-in-the-loop boundary" để tăng điểm trách nhiệm và độ tin cậy.

### Đánh giá
**7.5/10**

---

## 4. Feedback Loop

### Điểm mạnh
Project đã có nền tảng dữ liệu rất tốt để xây feedback loop sau này:
- transcript,
- runtime events,
- final review,
- summary payload,
- company knowledge citations.

Điều này nghĩa là bạn đã có **telemetry và memory candidates/session** đủ để phát triển vòng học hỏi.

### Điểm yếu cốt lõi
Hiện tại feedback loop mới ở mức:
- **collect data**

chứ chưa ở mức:
- **use feedback to improve future behavior**.

Đây là khoảng trống lớn nhất nếu bám sát chủ đề hackathon.

### Những gì chưa thấy đủ rõ
- HR chấm lại kết quả AI,
- hệ thống cập nhật rubric/weights,
- lần interview sau dùng chiến lược khác,
- có before/after để chứng minh improvement.

### Cải tiến đề xuất
#### P0
1. Thêm form **HR Feedback on AI Evaluation** sau review:
   - overall agreement score,
   - competency misjudged,
   - missing evidence,
   - false positive / false negative notes.
2. Lưu feedback thành structured data theo session.
3. Tạo rule-based recalibration đơn giản cho MVP:
   - nếu HR liên tục đánh thấp hơn AI ở competency X, giảm weight hoặc tăng threshold cho competency X.
4. Hiển thị audit trail:
   - "Rubric updated after 5 HR feedback records."

#### P1
5. Thêm dashboard nhỏ:
   - AI recommendation agreement rate,
   - score delta giữa AI và HR,
   - top failure reasons.
6. Demo được một case:
   - lần 1 AI đánh giá sai,
   - HR sửa,
   - lần 2 hệ thống hỏi/chấm cẩn thận hơn.

### Đánh giá
**5.5/10**

---

## Project hiện tại là agentic AI hay chưa?

### Câu trả lời ngắn
**Có, nhưng chưa fully demonstrated.**

### Câu trả lời chính xác hơn
InterviewX hiện tại đã vượt qua mức chatbot hoặc AI feature bình thường vì nó có:
- goal-oriented workflow,
- multi-step execution,
- tool use,
- session/state continuity,
- partial autonomy.

Tuy nhiên, để được nhìn nhận là một **agentic system mạnh theo chủ đề hackathon**, project vẫn cần:
- explicit plan representation,
- explicit adaptive decision logging,
- explicit closed-loop improvement.

Nói cách khác:

> InterviewX đã có agentic backbone, nhưng chưa show hết agentic behavior trong product/demo.

---

## Khoảng cách giữa narrative và implementation

Trong hồ sơ dự án, InterviewX được mô tả như hệ thống multi-agent gồm:
- Orchestrator,
- CV Screener,
- Interviewer,
- Evaluator,
- Scheduler.

Narrative này rất tốt để pitch. Tuy nhiên trong implementation hiện tại, giám khảo kỹ thuật có thể nhìn thấy nó giống:
- một hệ service-based architecture,
- có AI ở nhiều bước,
- nhưng chưa có biểu hiện rất rõ của multi-agent handoff và self-directed control.

### Điều này không hẳn là vấn đề
Bạn **không cần** biến toàn bộ hệ thống thành framework multi-agent phức tạp chỉ để hợp chủ đề.

Điều bạn cần là:
1. chứng minh mỗi "agent role" có trách nhiệm rõ,
2. chứng minh có handoff và decision boundary,
3. chứng minh có memory / feedback / adaptation.

---

## Kế hoạch cải tiến đề xuất theo mức ưu tiên

## P0 — nên làm ngay trước vòng pitching / nộp vòng 2

### 1. Agent Goal + Interview Plan hiển thị rõ trong UI
**Tác động:** tăng điểm Goal-driven + Planning ngay lập tức.

Cần có:
- goal của session,
- competency map,
- current phase,
- next intended step.

### 2. Decision Log
**Tác động:** tăng điểm Autonomy mạnh nhất.

Mỗi decision nên có:
- decision type,
- timestamp,
- reason,
- evidence,
- confidence,
- chosen next action.

### 3. HR Feedback form đơn giản
**Tác động:** biến Feedback Loop từ concept thành feature thật.

Có thể chỉ cần:
- AI score vs HR score,
- đồng ý / không đồng ý,
- lý do.

### 4. Demo script thể hiện rõ agentic behavior
**Tác động:** tăng khả năng thuyết phục mà chưa cần code quá sâu.

Demo nên có ít nhất 1 ví dụ:
- ứng viên trả lời mạnh ở backend,
- agent đổi hướng đào sâu system design,
- sau đó HR đánh giá lại,
- hệ thống lưu feedback.

---

## P1 — nên làm nếu còn thời gian

### 5. Plan adjustment events
- `plan.created`
- `plan.adjusted`
- `plan.completed`

### 6. Confidence-based routing
- confidence cao: auto recommendation,
- confidence thấp: escalate cho HR.

### 7. Agent performance metrics
- competency coverage,
- interview completion rate,
- recommendation agreement rate,
- average score delta AI vs HR.

### 8. Session replay / observability view
Cho giám khảo thấy hệ thống không phải black box.

---

## P2 — hướng dài hạn sau hackathon

### 9. Adaptive policy updates
Cập nhật policy hỏi/chấm theo feedback history.

### 10. Better grounded memory
Tận dụng transcript, JD, company docs, candidate history như context có kiểm soát.

### 11. Anti-cheating signals as agent inputs
Nếu có tab switching / suspicious timing / consistency drift, agent thay đổi cách hỏi hoặc giảm confidence.

---

## Gợi ý thông điệp khi pitch

### Cách mô tả đúng bản chất hiện tại
> InterviewX không chỉ dùng AI để trả lời câu hỏi, mà dùng AI để theo đuổi một mục tiêu tuyển dụng cụ thể: hiểu JD, lập kế hoạch interview, thực hiện phỏng vấn sơ bộ, đánh giá theo bằng chứng, và dần cải thiện từ phản hồi của HR.

### Cách trả lời nếu giám khảo hỏi “vì sao đây là agentic AI?”
> Vì hệ thống không hoạt động như một chatbot một lượt. Nó giữ mục tiêu xuyên suốt, chia mục tiêu thành nhiều bước, sử dụng công cụ bên ngoài như LiveKit và knowledge retrieval để hành động, tự cập nhật trạng thái theo diễn biến buổi phỏng vấn, và đang được mở rộng để học từ feedback của HR qua từng session.

### Cách trả lời nếu giám khảo hỏi “feedback loop của bạn đang ở đâu?”
> Hiện tại chúng tôi đã có đầy đủ transcript, runtime events và session review để tạo learning signal. Trong phiên bản tiếp theo, HR feedback sẽ được cấu trúc hóa để recalibrate rubric và threshold, giúp lần đánh giá sau sát hơn với tiêu chuẩn thực tế của doanh nghiệp.

---

## Checklist tự kiểm tra trước khi demo

### Goal-driven
- [ ] Có nói rõ goal của agent chưa?
- [ ] Có outcome nghiệp vụ đo được chưa?

### Planning
- [ ] Có plan view hoặc plan artifact chưa?
- [ ] Có giải thích vì sao hỏi câu này tiếp theo chưa?

### Autonomy
- [ ] Có decision log chưa?
- [ ] Có ví dụ agent tự đổi hướng khi tình huống thay đổi chưa?

### Feedback Loop
- [ ] Có form HR feedback chưa?
- [ ] Có lưu feedback thành structured data chưa?
- [ ] Có thể trình bày lần sau hệ thống cải thiện ra sao chưa?

---

## Kết luận cuối

InterviewX đã có nền móng rất tốt để được xem là một sản phẩm **agentic AI có giá trị thực tiễn**, đặc biệt ở bài toán tuyển dụng tiếng Việt. Điểm cần làm ngay không phải là tăng thêm quá nhiều tính năng, mà là **làm lộ rõ hơn hành vi agentic vốn đã có** và **bổ sung vòng phản hồi khép kín ở mức MVP**.

Nếu chỉ được chọn một ưu tiên quan trọng nhất, nên làm:

> **Decision visibility + feedback loop MVP**

vì đây là hai thứ giúp project chuyển từ “workflow có AI” sang “agentic system có khả năng tự hành động và tự cải thiện”.

---

## Tài liệu tham khảo ngắn

Các ý trong tài liệu này tham chiếu từ:
- Agent GPA / Goal-Plan-Action evaluation frameworks,
- capstone demo checklists cho agentic systems,
- reliability / observability frameworks cho autonomous agents,
- và đối chiếu trực tiếp với codebase hiện tại của InterviewX.
