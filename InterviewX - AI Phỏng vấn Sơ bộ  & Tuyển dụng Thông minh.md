# **HỒ SƠ DỰ ÁN**

# **GDGoC HACKATHON VIETNAM 2026**

### 

### **Tên đội: *Đắng Team***

### **Thành Viên**

| STT | Họ và tên | Vai trò |
| :---: | :---: | :---: |
| **1** | **Nguyễn Viết Linh** | **Team Lead/ Ai**  |
| **2** | **Vũ Trang Nhung** | **BA** |
| **3** | **Phùng Thùy Trang**  | **Content Generation & Calibration** |
| **4** | **Hà Huyền Trang** | **UX/UI** |

# 1\. Tổng quan dự án

### 1.1 Tên dự án

***InterviewX \- AI Phỏng vấn Sơ bộ  & Tuyển dụng Thông minh***

### 1.2 Mô tả ngắn gọn

- ***Vấn đề:** Tuyển dụng tại Việt Nam đang lãng phí nghiêm trọng \- SME tốn 2-3 tháng và 32-81M VND mỗi vị trí qua headhunter, còn Big Tech nhận 500 \- 2000 CV/vị trí khiến HR quá tải, screen không kịp và mất ứng viên tốt, trong khi chưa có nền tảng AI phỏng vấn nào hỗ trợ tiếng Việt.*  
-   ***Giải pháp:** InterviewX là AI Agent tự screen CV, tự phỏng vấn ứng viên qua video call 24/7 bằng giọng nói tiếng Việt với câu hỏi adaptive, tự đánh giá theo 4 chiều và xếp hạng \- để HR chỉ cần gặp những người đã được AI validate.*  
-   ***Đối tượng hưởng lợi:** SME tiết kiệm 80% thời gian và 95% chi phí tuyển dụng, Enterprise tăng throughput HR gấp 10x, ứng viên được phỏng vấn 24/7 không cần xin nghỉ làm, và sinh viên/người lao động vùng xa được luyện phỏng vấn miễn phí qua AI Career Coach (SDG \#8 & \#10).*

### 1.3 Dự án sử dụng Agentic AI như thế nào?

 InterviewX không phải chatbot trả lời câu hỏi \-  mà là một hệ thống Multi-Agent gồm 5 agent chuyên biệt (Orchestrator, CV Screener, Interviewer, Evaluator, Scheduler) tự phối hợp để hoàn thành mục tiêu tuyển dụng từ đầu đến cuối mà không cần HR can thiệp ở giữa.

- ***Tự lập kế hoạch và thực hiện nhiều bước:** Khi HR nhập Job Description, Orchestrator Agent tự phân tích yêu cầu → lập interview plan → phân bổ thời gian cho từng competency (Technical, Problem-solving, Culture fit, Motivation) → quyết định thứ tự câu hỏi → ưu tiên ứng viên nào phỏng vấn trước dựa trên CV match score. Toàn bộ pipeline 5 bước (phân tích JD → screen CV → phỏng vấn → chấm điểm → xếp lịch) được Agent tự thực hiện tuần tự mà không cần con người trigger từng bước.*  
- ***Sử dụng công cụ bên ngoài:** Interview Agent gọi LiveKit API để tạo video call real-time, sử dụng Google Cloud Chirp 3 (STT) để nghe tiếng Việt, Gemini 3.1-Pro để reasoning và sinh câu hỏi follow-up, Google Cloud TTS để trả lời bằng giọng nói. CV Screener Agent truy vấn Firebase Firestore để lấy dữ liệu CV/JD. Scheduler Agent gọi SMTP API để tự gửi email mời phỏng vấn và reminder cho ứng viên chưa phản hồi.*  
- ***Phân tích và ra quyết định tự chủ:** Trong buổi phỏng vấn, Agent tự quyết định real-time: ứng viên trả lời tốt → hỏi khó hơn, trả lời yếu → chuyển hướng sang competency khác. Agent tự đánh giá chất lượng câu trả lời, tự quyết định khi nào đủ thông tin để dừng, tự reject ứng viên không đạt ngưỡng, và tự advance ứng viên tốt sang vòng tiếp theo tất cả không cần HR phê duyệt từng bước. Tất cả được định nghĩa trước theo ngưỡng điểm và định hướng phỏng vấn của HR, nếu HR không cho phép tự động advance / reject thì Agent có khả năng gửi điểm đánh giá , tóm tắt cuộc phỏng vấn, những điểm key đáng chú ý cho HR để HR quyết định, sau khi HR quyết định thì Agent mới gửi mail cho ứng viên.*   
- ***Ghi nhớ thông tin và bối cảnh:** Agent ghi nhớ toàn bộ context trong suốt buổi phỏng vấn \- nếu ứng viên đề cập kinh nghiệm microservices ở phút thứ 3, Agent có thể hỏi lại chi tiết ở phút thứ 15\. Quan trọng hơn, hệ thống có feedback loop dài hạn: sau phỏng vấn thật, HR đánh giá accuracy (ví dụ "AI chấm 85% nhưng thực tế 60%") → Agent tự điều chỉnh rubric và trọng số chấm điểm cho các lần sau, ngày càng chính xác hơn theo thời gian.*

# 2\. Vấn đề và giải pháp

### 2.1 Đặt vấn đề

***Vấn đề này ảnh hưởng đến ai?***

-    *920K+ SME Việt Nam (98% tổng DN) tuyển dụng thủ công, tốn vài tháng mỗi vị trí.*  
-   *Big Tech (FPT, VNG, Viettel, MoMo) nhận 500-2000 CV/vị trí, HR quá tải screen không kịp, mất ứng viên tốt.*  
-   *Ứng viên phải xin nghỉ làm phỏng vấn giờ hành chính, chờ hàng tuần không phản hồi.*

  ***Tại sao vấn đề này quan trọng?***

- *Headhunter quá đắt: 18-27% lương năm (32-81M VND/lần), SME không kham nổi.*  
- *Đa số phỏng vấn sơ bộ không dẫn đến tuyển dụng dẫn đến lãng phí cả hai bên.*  
- *Turnover 24% → tuyển lại liên tục, chi phí tuyển sai \= 30-150% lương năm.*  
-  *Chỉ 25.7% DN dùng công nghệ (VCCI), thị trường recruitment software VN chỉ $9.52M*  

  ***Các giải pháp hiện tại còn hạn chế gì?***

-   *TopCV, VietnamWorks, CareerViet: job board truyền thống, zero AI, HR vẫn phải screen thủ công.*  
-   *HireVue ($35K+/năm): có AI interview nhưng không tiếng Việt, giá enterprise-only, từng bị kiện bias.*  
-   *Interviewer.AI ($500-850/năm): chỉ async video (không real-time), không tiếng Việt.*  
-   *Hire-Central.ai (VN): chỉ ATS, không có AI phỏng vấn.*  
-   *Chưa có nền tảng nào cung cấp AI video interview real-time tiếng Việt cho thị trường Việt Nam.*

### 2.2 Câu hỏi đặt ra

-  *Làm thế nào để AI tự vận hành toàn bộ quy trình tuyển dụng từ screen CV đến phỏng vấn sơ bộ mà không cần HR can thiệp từng bước?*  
-  *Làm sao để AI phỏng vấn real-time bằng giọng nói tiếng Việt với chất lượng tương đương phỏng vấn viên thật?*  
-  *Làm sao để AI sử dụng đồng thời nhiều công cụ (video call, speech-to-text, LLM, database) phối hợp mượt mà trong một buổi phỏng vấn 15-20 phút?*  
-   *Làm sao để đảm bảo AI đánh giá ứng viên minh bạch, công bằng, và có khả năng tự cải thiện qua feedback từ HR?*

# 2.3. Giải pháp đề xuất

  InterviewX là hệ thống Multi-Agent gồm 5 agent chuyên biệt phối hợp dưới Orchestrator Agent, tự vận hành toàn bộ recruitment pipeline từ khi HR đăng JD đến khi ứng viên được hẹn lịch phỏng vấn trực tiếp.

-   Các bước chính:  
  - HR nhập Job Description → Orchestrator phân tích và tự sinh bộ câu hỏi theo 4 chiều: Technical, Problem-solving, Culture fit, Motivation  
  - Upload CV → CV Screener Agent phân tích, xếp hạng match score → tự gửi link video call cho ứng viên đạt ngưỡng  
  - Ứng viên vào link → Interview Agent phỏng vấn 15-20 phút qua video call bằng giọng nói tiếng Việt, hỏi adaptive ( nếu ứng viên trả lời tốt →hỏi nhiều câu khó hơn, còn nếu yếu → chuyển hướng sang các câu hỏi khác)  
  - Evaluate Agent chấm điểm 4 chiều, giải thích lý do, highlight trích đoạn đáng chú ý  
  - HR review dashboard → chọn top → Scheduler Agent tự gửi email hẹn lịch → HR rate accuracy → Agent tự cải thiện  
-   Điểm khác biệt:  
  - First-mover: AI video interview real-time tiếng Việt   
  - Dual-market: SME dùng Agent thay HR, Enterprise dùng Agent scale HR gấp 10x trên cùng một core AI  
  - Observable AI: HR nhìn thấy Agent đang đánh giá gì, quyết định gì, dựa trên trích dẫn câu trả lời cụ thể  
  - Career Coach miễn phí: cross-subsidy model tạo tác động xã hội bền vững

Anti-cheating tích hợp: Phát hiện gian lận real-time bằng MediaPipe on-device \- tính năng chưa có ở bất kỳ đối thủ nào trên thị trường VN

-   Tính năng chính:  
  -  AI video interview real-time tiếng Việt với adaptive questioning từ HR quy định trước hoặc linh động cho từng ứng viên  
  -  Tự động screen CV và xếp hạng match score  
  -  Scorecard 4 chiều với explanation và highlights  
  -  Dashboard cho HR review, so sánh ứng viên  
  -  Feedback loop: HR rate accuracy → Agent tự điều chỉnh rubric  
  -  Career Coach mode miễn phí cho sinh viên luyện phỏng vấn

 Chống gian lận thông minh: AI phát hiện đọc bài, nhờ người khác trả lời, sử dụng AI tool \- đảm bảo tính trung thực của buổi phỏng vấn

# 3\. Công nghệ dự kiến sử dụng

### 3.1 Công nghệ AI

- *LLM: Gemini 3.1 Pro \- multimodal, hỗ trợ tiếng Việt, reasoning nhanh, làm được những việc phức tạp*  
- *Framework AI Agent: Google ADK (Agent Development Kit) \- tối ưu cho Gemini, hỗ trợ multi-agent hierarchy và tool calling*  
-  *Speech-to-Text: Google Cloud Chirp 3*  
- *Text-to-Speech: Google Cloud TTS (WaveNet Vietnamese) \+ Viettel AI TTS (fallback) hoặc sử dụng gemini-2.5-flash-native-audio-preview-12-2025 cho toàn bộ nhiệm vụ speech*  
- *Real-time Voice AI: LiveKit Agents SDK \- turn-taking detection, barge-in, VAD built-in*  
- *Embedding Model: Gemini Text Embedding (text-embedding-004)  dùng để chuyển CV, JD, transcript thành vector để semantic search*

***Anti-cheating AI**: Google MediaPipe (open-source, Apache 2.0) \- Face Detection, Face Mesh 468 landmarks chạy on-device trong browser qua WASM \+ WebGL, không cần gửi video lên server, bảo mật cao.*

### 3.2 Hạ tầng

- *Google Cloud Platform \- nền tảng chính cho AI services và deploy*  
- *Google Cloud Run \- serverless, auto-scale, chỉ trả tiền khi dùng*  
- *Firebase (Firestore \+ Auth) \- real-time database và authentication*  
- *LiveKit Cloud \- managed WebRTC infrastructure cho video call*  
- *Docker \- containerization cho development và deployment*

### 3.3 Công nghệ phát triển

- *Frontend: React \+ LiveKit React SDK (video UI components sẵn có)*  
- *Backend: Typescript (Google ADK, LiveKit Agents SDK)*  
- *Database: Firebase Firestore (NoSQL, real-time sync)*  
- *Vector Database: ChromaDB \- lưu trữ embedding cho RAG và AI memory*  
-  *AI Pipeline: Google ADK → Gemini 3.1 Pro → Chirp 3 (STT) → Google TTS → LiveKit (streaming)*

# 3.4. Điểm mạnh cạnh tranh

-  First-mover: AI video interview real-time tiếng Việt  chưa có đối thủ nào trên thị trường  tối ưu cho tiếng việt ( Một số bên hiện tại đã có nhưng tối ưu cho tiếng anh và kinh phí cao như HireVue/[Interviewer.AI](http://interviewer.ai) )  
-  Dual-market: Cùng một core AI phục vụ cả SME (Agent thay HR) lẫn Enterprise (Agent scale HR 10x)   
-  Real-time 2 chiều: Phỏng vấn video call giống người thật với adaptive follow-up, không phải ghi hình 1 chiều hay chatbot text  
-  Cultural calibration: Hiểu văn hóa giao tiếp Việt Nam \- không đánh giá sai ứng viên vì phong cách khiêm tốn, gián tiếp  
-  Giá cạnh tranh: Phù hợp với nhiều định hướng của từng công ty   
-  Tác động xã hội: Career Coach miễn phí qua cross-subsidy 

### 3.5. Chống gian lận trong phỏng vấn

Vấn đề: Khi AI phỏng vấn thay người, ứng viên có thể gian lận bằng cách đọc đáp án từ màn hình khác, nhờ người ngoài khung hình nhắc bài, hoặc dùng ChatGPT/Gemini generate câu trả lời real-time. InterviewX tích hợp nhiều lớp phòng chống:

- **Adaptive Deep Probing (P0 \- không cần thêm công nghệ):** Gemini tự phát hiện câu trả lời quá hoàn hảo hoặc generic → hỏi follow-up cực kỳ cụ thể buộc ứng viên giải thích sâu. Yêu cầu cho ví dụ thực tế, giải thích lại bằng cách khác, liên kết ngược với câu trả lời trước \- AI-generated answers không có depth khi bị probe  
- **Tab Switching Detection (P0 \-5 dòng code)**: React frontend dùng ***document.visibilitychange*** API phát hiện khi ứng viên chuyển tab (tra ChatGPT). Log số lần và thời điểm chuyển tab, flag trong Scorecard cho HR review  
- **Response Timing Analysis (P1)**: Phân tích thời gian từ khi Agent hỏi đến khi ứng viên trả lời. Pattern bất thường: pause dài bất thường (chờ AI generate) rồi trả lời fluent ngay lập tức. So sánh với baseline timing của câu trả lời tự nhiên  
- **Face Verification (P1)**: Google MediaPipe Face Detection so sánh khuôn mặt trong video call với ảnh trên CV/CCCD. Continuous face matching suốt buổi phỏng vấn \- phát hiện nếu đổi người giữa chừng  
- **Gaze Tracking (P2):** MediaPipe Face Mesh (468 landmarks) theo dõi hướng nhìn. Phân biệt "suy nghĩ" (nhìn lên/xa) vs "đọc bài" (mắt di chuyển theo dòng text). Chạy hoàn toàn on-device trong browser qua WASM \+ WebGL, chỉ sample 2-5 FPS \- không ảnh hưởng hiệu năng video call  
- **Behavioral Consistency Scoring (P2):** Gemini phân tích sự nhất quán giữa nội dung CV vs câu trả lời, câu trả lời đầu vs cuối buổi, mức độ tự tin trong giọng nói vs nội dung. Output: Consistency Score trong Scorecard  
- **Lưu ý**: Tất cả kết quả anti-cheating chỉ là flag/score trong Scorecard cho HR tham khảo, không tự động loại ứng viên \- giữ nguyên tắc Human-in-the-loop

# 4\. Đối tượng sử dụng

- SME (10-200 nhân viên): Không có HR chuyên nghiệp hoặc HR team nhỏ 1-2 người, tuyển 3-10 vị trí/năm, cần giải pháp nhanh-rẻ-hiệu quả. Ngành: F\&B, Retail, IT, Logistics.  
-  Enterprise / Big Tech (200+ nhân viên): FPT, VNG, Viettel, MoMo, Shopee VN, startups scale-up hàng ngày nhận 500-2000 CV/vị trí, cần AI scale throughput HR để không mất ứng viên tốt.  
-  Công ty tuyển dụng / Headhunter: Dùng InterviewX như công cụ screen sơ bộ hàng loạt trước khi giới thiệu ứng viên cho khách hàng.  
-  Sinh viên / Người lao động (miễn phí): Luyện phỏng vấn với AI Career Coach, nhận feedback chi tiết, cải thiện kỹ năng  đặc biệt người vùng xa khó tiếp cận cơ hội

# 5\. Tính khả thi

# 5.1. Kế hoạch phát triển

Trong thời gian hackathon (4 tuần):

- Tuần 1-2: Core AI interview engine \- tích hợp LiveKit \+ Gemini \+ Chirp 3, prototype adaptive questioning tiếng Việt  
- Tuần 3: CV Screener Agent \+ Evaluate Agent \+ HR Dashboard  
- Tuần 4: Polish, testing với native speakers, Career Coach mode, chuẩn bị demo

  Demo scope vòng 2-3:

- Live demo: HR nhập JD → Agent sinh câu hỏi → AI video interview 1 ứng viên (15 phút, tiếng Việt) → Scorecard 4 chiều  
- Architecture demo: CV screening batch, email scheduling, feedback loop \- trình bày qua slides

  Roadmap sản phẩm:

-  Q2 2026 \- MVP: Core AI interview \+ CV screening, pilot 50 SME \+ 5 Enterprise  
-  Q3-Q4 2026 \- Growth: ATS integration, partnership TopCV/CareerViet, mở rộng F\&B/Retail/IT  
-  2027 \- Scale: Mở rộng các tính năng, xây dựng nhiều pipline hỗ trợ nhiều công ty hơn

  Tính khả thi thực tế:

-  Đã có nhiều công ty có sản phẩm: Trên thế giới đã có nhiều bên xây dựng và hiện tại công nghệ đã hỗ trợ nhiều như LiveKit cho streaming với ai , Gemini 3.1 Pro với điểm suy luận cao, hoàn toàn phù hợp với xu hướng ai agent hiện tại   
-  Phù hợp chính sách: Chính phủ VN hỗ trợ 300K SME chuyển đổi số đến 2030, 40% quỹ NATIF ưu tiên AI  
-  Thị trường sẵn sàng: 57% DN có kế hoạch tuyển thêm (Adecco Q2/2025), nhu cầu rất lớn

# 5.2. Ngân sách dự kiến

*Chi phí AI (Gemini 3.1 Pro):*

- *Input: $2/1M tokens (câu lệnh ≤ 200K tokens)*  
- *Output: 120K VND/1M tokens (câu lệnh ≤ 200K tokens)*  
- *Context caching: $0.20/1M tokens \+ $4.5/1M tokens/giờ lưu trữ*  
- *Google Search grounding: 5,000 câu lệnh miễn phí/tháng, sau đó $14/1,000 queries*

  *Ước tính chi phí AI mỗi cuộc phỏng vấn 15-20 phút:*

- *Gemini 3.1 Pro Input: \~60K tokens (JD \+ CV \+ context \+ transcript tích lũy) → \~3K VND*  
- *Gemini 3.1 Pro Thinking: \~36K thinking tokens (reasoning chọn câu hỏi, đánh giá real-time) → \~4.3K VND*  
- *Gemini 3.1 Pro Output → Text cho TTS: \~6K tokens (câu hỏi \+ follow-up sinh ra để chuyển sang giọng nói) → \~720 VND*  
- *Gemini Scorecard cuối phỏng vấn: \~5K tokens (thinking \+ đánh giá 4 chiều \+ highlights) → \~360 VND*  
-  *Google Cloud STT (Chirp 3): 20 phút ứng viên nói × $0.016/phút → \~8K VND*  
-  *Google Cloud TTS: \~8,000 ký tự AI nói × $16/1M ký tự → \~3.2K VND*  
-  *LiveKit Cloud: 20 phút video call × $0.01/phút → \~5K VND*  
-  *ChromaDB \+ RAG query: embed CV/JD \+ retrieve context → \~250 VND*  
-  *Tổng mỗi cuộc phỏng vấn: \~20K VND (\~$0.80)*

  *Hạ tầng hàng tháng:*

-   *Firebase Firestore: Free tier đủ cho MVP, Blaze plan \~$5-10/tháng khi scale*  
-   *Google Cloud Run: Free 2M requests/tháng, sau đó \~$5-10/tháng*  
-   *ChromaDB: Open-source, miễn phí*  
-   *Domain \+ SSL: \~$10/năm*

  *Tổng chi phí hackathon: \~$30-50/tháng (chủ yếu STT \+ LiveKit, LLM dùng free tier giai đoạn dev).*

# 6\. Tài liệu tham khảo

\[1\] VietnamPlus, "PM Pham Minh Chinh urges SMEs to break limits for growth," 2024\. \[Online\]. Available: [https://en.vietnamplus.vn/pm-pham-minh-chinh-urges-smes-to-break-limits-for-growth-post310717.vnp](https://en.vietnamplus.vn/pm-pham-minh-chinh-urges-smes-to-break-limits-for-growth-post310717.vnp)

\[2\] ManpowerGroup Vietnam, "Vietnam Salary Guide 2025," 2025\. \[Online\]. Available: [https://www.manpower.com.vn/en/insights/vietnam-salary-guide/2025](https://www.manpower.com.vn/en/insights/vietnam-salary-guide/2025)

\[3\] Talentnet-Mercer, "Vietnam Total Remuneration Survey 2025," 2025\. \[Online\]. Available: [https://www.talentnetgroup.com/vn/featured-insights/rewards/vietnam-salary-report-labor-market-2025](https://www.talentnetgroup.com/vn/featured-insights/rewards/vietnam-salary-report-labor-market-2025)

\[4\] IMARC Group, "Vietnam Recruitment Software Market Size Report 2033," 2024\. \[Online\]. Available: [https://www.imarcgroup.com/vietnam-recruitment-software-market](https://www.imarcgroup.com/vietnam-recruitment-software-market)

\[5\] Mordor Intelligence, "AI Recruitment Market \- Industry Report," 2025\. \[Online\]. Available: [https://www.mordorintelligence.com/industry-reports/ai-recruitment-market](https://www.mordorintelligence.com/industry-reports/ai-recruitment-market)

\[6\] Adecco Vietnam, "Vietnam Talent Market Update Q2/2025," 2025\. \[Online\]. Available: [https://www.adecco.com/en-vn/insights/vietnam-talent-market-update-q2-2025](https://www.adecco.com/en-vn/insights/vietnam-talent-market-update-q2-2025)

\[7\] Staffing Industry Analysts, "Vietnam Employee Turnover Rate on the Rise," 2026\. \[Online\]. Available: [https://www.staffingindustry.com/news/global-daily-news/vietnam-employee-turnover-rate-rise-vietnam-news](https://www.staffingindustry.com/news/global-daily-news/vietnam-employee-turnover-rate-rise-vietnam-news)

\[8\] Vietnam Law Magazine, "Digital Transformation an Urgent Need for SMEs," 2024\. \[Online\]. Available: [https://vietnamlawmagazine.vn/digital-transformation-an-urgent-need-for-smes-59216.html](https://vietnamlawmagazine.vn/digital-transformation-an-urgent-need-for-smes-59216.html)

\[9\] VnEconomy, "Vietnam Launches Digital Transformation Plan for SMEs," 2026\. \[Online\]. Available: [https://en.vneconomy.vn/vietnam-launches-digital-transformation-plan-for-small-and-medium-sized-enterprises.htm](https://en.vneconomy.vn/vietnam-launches-digital-transformation-plan-for-small-and-medium-sized-enterprises.htm)

\[10\] VietnamNet, "Technology, Innovation, Digital Transformation: Vietnam's Triple Push in 2026," 2026\. \[Online\]. Available: [https://vietnamnet.vn/en/technology-innovation-digital-transformation-vietnam-s-triple-push-in-2026-2479600.html](https://vietnamnet.vn/en/technology-innovation-digital-transformation-vietnam-s-triple-push-in-2026-2479600.html)

\[11\] Chính phủ Việt Nam, "Nghị định 13/2023/NĐ-CP về Bảo vệ Dữ liệu Cá nhân," 2023\. \[Online\]. Available: [https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-13-2023-ND-CP-bao-ve-du-lieu-ca-nhan-540334.aspx](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-13-2023-ND-CP-bao-ve-du-lieu-ca-nhan-540334.aspx)

\[12\] Google, "Gemini API Documentation & Pricing," 2026\. \[Online\]. Available: [https://ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)

\[13\] Google, "Agent Development Kit (ADK) Documentation," 2026\. \[Online\]. Available: [https://google.github.io/adk-docs/](https://google.github.io/adk-docs/)

\[14\] Google Cloud, "Chirp 3 \- Speech-to-Text for Vietnamese," 2026\. \[Online\]. Available: [https://cloud.google.com/speech-to-text/docs/models/chirp-3](https://cloud.google.com/speech-to-text/docs/models/chirp-3)

\[15\] LiveKit Inc., "LiveKit Agents Framework Documentation," 2026\. \[Online\]. Available: [https://docs.livekit.io/agents/](https://docs.livekit.io/agents/)

\[16\] ChromaDB, "Chroma \- Open-source Vector Database," 2026\. \[Online\]. Available: [https://docs.trychroma.com/](https://docs.trychroma.com/)

\[17\] VMLU, "Vietnamese Multitask Language Understanding Benchmark," 2025\. \[Online\]. Available: [https://vmlu.ai/](https://vmlu.ai/)

\[18\] MarketIntelo, "AI Video Interview Market \- $1.42B (2024), CAGR 20.8%," 2024\. \[Online\]. Available: [https://marketintelo.com/report/ai-video-interview-analysis-market/](https://marketintelo.com/report/ai-video-interview-analysis-market/)

# 7\. Thông tin liên hệ

Email: dangstudio24@gmail.com  
Số điện thoại: 0981601209

