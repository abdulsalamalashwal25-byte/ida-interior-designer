# PHASE 01 — SPACE ANALYSIS
## ARCHITECTURE **R02 — DELTA / AMENDMENT**

**DELTA ONLY — لا كود · لا Schema · لا Master · لا RULES · لا Intake · لا تعديل A–F · لا تعديل الطبقة التأسيسية · لا تغيير نطاق Phase 01 · لا Implementation.**

> **R01 سارٍ كما هو** عدا ما تعدّله هذه الدلتا (**§7 Constraints Model** · **§4/§6 حدود الهندسة**).
> **الانحدار:** 1377/1377 · REGRESSIONS: NONE (لم يُمسّ شيء).

---

## 0. قياس يسند A-01

| # | القياس | النتيجة |
|---|---|---|
| **M-1** | بنية حكم B | **`Finding.__slots__ = (rule, location, message, severity)`** — و`severity` **يُسنده المدقّق وقت الإصدار** |
| **M-2** | مستويات الشدة المستعملة | **`ERROR` · `INFO`** (وWARNING واردة في العقد العام) |

**الأثر:** حكم B **كيان مملوك بشدته**. وأي تحويل مباشر منه إلى «قيد» **يعيد تفسير ملكية ليست لـPhase 01** — وهذا ما تصححه A-01.

---

## A-01 — فصل B Findings عن Phase 01 Constraints

### 1. الصياغة المسحوبة من R01 §7

~~«قيد حركة ← **حكم B4 مُستهلَك**» · «قيد فتحات ← `openings[]` + **حكم B5**» · «قيد عنصر ثابت ← بيانات العناصر الثابتة»~~

**الخلل المفاهيمي:** الجدول أوحى بأن **حكم B يصير قيدًا مباشرةً**، فاختفت خطوة وسيطة إلزامية: **حكم B هو دليل متاح، والتصنيف فعل تحليلي منفصل يملكه Phase 01 ويُعلنه باسمه.**

### 2. العقد النافذ — ثلاث خطوات لا تُختصر

```
[1] B Finding  /  Existing Fact          ← مملوك للمدقّق أو للماستر
        │   (يُنقل كما صدر · بشدته · بمالكه)
        ▼
[2] Evidence available to Phase 01       ← دليل متاح للتحليل
        │   (فعل تحليلي صريح باسم Phase 01)
        ▼
[3] Phase 01 Constraint Classification   ← تصنيف معلن، لا حكم هندسي جديد
```

**والممنوع:** `B Finding → Constraint` **تلقائيًا**.

### 3. القواعد الست

| # | القاعدة |
|---|---|
| **CB-1** | **Phase 01 لا يعيد تفسير `severity` الخاصة بـB** — تُنقل كما أصدرها مالكها (M-1) |
| **CB-2** | **لا تحويل تلقائي** لـ`ERROR`/`WARNING`/`INFO` إلى Constraint |
| **CB-3** | **يجوز** تسجيل أن نتيجة B **دليل ذو صلة بالتحليل** (`relevant evidence`) — وهذا **ليس تصنيفًا** |
| **CB-4** | **إن صنّفها Phase 01 قيدًا**, فالتصنيف: **مُعلن كتحليل Phase 01** · **مرتبط بـ`origin_path`/`evidence_ref`** · **لا يغيّر حكم B الأصلي** · **ليس Design Decision** · **ولا ينشئ `[C]` هندسيًا جديدًا** |
| **CB-5** | **أدلة غير كافية ⇒ `UNRESOLVED / NOT_CLASSIFIED`** — **ولا تخمين** |
| **CB-6** | **الفصل الثلاثي محفوظ:** `Engineering Validation ≠ Space Analysis Constraint ≠ Design Decision` |

### 4. نموذج Constraints المحدَّث (يحل محل §7 في R01)

| الحقل | المضمون |
|---|---|
| `constraint_id` | معرّف التصنيف التحليلي |
| **`evidence_ref`** | **مرجع الدليل** — حكم B أو حقيقة ماستر |
| **`evidence_kind`** | `B_FINDING` \| `MASTER_FACT` |
| **`origin_layer`** | **مالك الدليل** (B2…B5 · Master) — **لا يتغير** |
| **`origin_severity`** | **الشدة كما أصدرها مالكها** — **منقولة لا مُعاد تقييمها** |
| `origin_path` | المسار في الماستر |
| **`classification`** | `CONSTRAINT` \| **`NOT_CLASSIFIED`** \| **`UNRESOLVED`** |
| **`classified_by`** | **`PHASE_01_ANALYSIS`** — التصنيف معلن باسمه |
| `classification_basis` | لماذا صُنِّف — نصًا |
| **`alters_origin_verdict`** | **`false` دائمًا** |
| **`is_design_decision`** | **`false` دائمًا** |
| **`creates_master_fact`** | **`false` دائمًا** |

**مصادر الأدلة (بعد التصحيح):**

| الفئة | الدليل | من يملكه | من يصنّف |
|---|---|---|---|
| قيد هندسي | حقيقة مُصرَّحة | **Master** | Phase 01 |
| قيد حركة | **حكم B4 كدليل** | **B4** | Phase 01 |
| قيد فتحات | `openings[]` + **حكم B5 كدليل** | Master / **B5** | Phase 01 |
| قيد عنصر ثابت | `columns`/`beams`/`services` مُصرَّحة | **Master** | Phase 01 |
| قيد استخدام · قيد عميل | مدخل `[C]` | **Master** | Phase 01 |

**والفرص (§8) تخضع لنفس الفصل:** دليل ← ملاحظة تحليلية معلنة — **بلا تحويل تلقائي ولا قرار**.

---

## A-02 — حماية Master → Geometry → Output

### 1. القاعدة الصريحة المضافة

> ## **Phase 01 لا يصبح مصدرًا بديلًا للهندسة.**

**المسار الوحيد النافذ:**
```
Validated Master ──► C3 Geometry Assembly ──► Output
```

**والمسار الممنوع:**
```
✗ Validated Master ──► Phase 01 interpretation ──► new geometry ──► C3
```
**إلا بعقد مستقل ومعتمد يحدده صراحةً — ولا وجود له اليوم.**

### 2. القواعد الثماني

| # | القاعدة |
|---|---|
| **GA-1** | **Phase 01 لا يعيد بناء geometry** |
| **GA-2** | **لا يعدّل أي `coordinates` هندسية** |
| **GA-3** | **لا ينشئ أبعادًا هندسية مرجعية** |
| **GA-4** | **لا ينشئ wall/opening/furniture geometry بديلة** عن الماستر |
| **GA-5** | **أي قياس للتحليل يبقى `analytical_measurement`** — **ولا يتحول إلى Master fact** |
| **GA-6** | **O-1 يبقى Analytical Evidence** — لا Class A ولا هندسة |
| **GA-7** | **C3 لا يعتمد على تفسير Phase 01** لإعادة إنشاء الهندسة الأصلية |
| **GA-8** | **DEC-P01-05 يبقى OPEN** — ولا يُحسم ذاتيًا |

### 3. صياغة المسؤولية المعتمدة

> **C3 owns geometric representation.**
> **Phase 01 owns spatial analysis of declared geometry.**
> **Phase 01 does not become a geometry authority.**

### 4. أثر ذلك على القياس التحليلي (توضيح DEC-P01-04)

القياس المسموح **للعرض والمقارنة فقط**, ويحمل: `analytical_measurement: true` · `is_master_fact: false` · `stored_in_master: false` · `consumable_by_c3: false`.
**وDEC-P01-04 يبقى OPEN** — لم يُحسم بهذه الدلتا.

---

## 3. أثر التعديل على R01

| القسم | الأثر |
|---|---|
| **§7 Constraints Model** | **مُستبدَل** بالعقد الثلاثي وحقوله الاثني عشر (A-01) |
| **§8 Opportunities Model** | **توضيح**: يخضع لنفس الفصل — بلا تغيير في جوهره |
| **§4 Outputs (O-1)** | **تشديد**: `Analytical Evidence` + **GA-6/GA-7** |
| **§6 Existing-State Model** | **تشديد**: GA-1…GA-5 — التمثيل نقل لا إعادة بناء |
| **§5 / §13 Ownership** | **إضافة الصياغة الثلاثية** (A-02.3) |
| **§10 Spatial Relationships** | بلا تغيير — و`NOT_PROVABLE` سارية |
| **§21 Threat Model** | **T-08** يتشدد بـCB-1/CB-2 · **T-01** يتشدد بـGA-1…GA-4 |
| **§0 · §1 · §2 · §9 · §11 · §12 · §14…§20 · §22** | **سارية بلا تغيير** |

**ولم يتغير نطاق Phase 01.**

---

## 4. DECISIONS / GAPS — بلا تغيير

### القرارات — **كلها OPEN**
**DEC-P01-01** · **DEC-P01-02** · **DEC-P01-03** · **DEC-P01-04** · **DEC-P01-05** · **DEC-P01-06** · **DEC-P01-07** — **لم يُحسم أيٌّ منها، ولم يُضف جديد.**

### الثغرات — **كلها OPEN**
**GAP-P01-01** (لا بنية للقيود/الفرص/التجاور) · **GAP-P01-02** (لا `presence_register` لـ`zones`) · **GAP-P01-03** (Visibility غير قابلة للإثبات) · **GAP-P01-04** (حجية مخرجات Phase 01 غير معرَّفة في §10).

**وثغرات الطبقات السابقة:** GAP-P1-02 (سببها مُصحَّح · حالتها قرار المشرف) · GAP-01 · GAP-02 · CONFLICT-E-01 · GAP-D-01 · GAP-F-01/02/03 · CLG-F-01 · GAP-C-02 · GAP-C6-02…05 · GAP-E-01 · DEC-C2-01…08 · DEC-E-02…05 · DEC-F-02…05 · DEC-P1-01…07 — **كلها OPEN كما هي**.

**لم أغلق أي GAP أو DEC، ولم أُنشئ جديدًا.**

---

## 5. ما لم يتغير — تأكيد A-04

| البند | الحالة |
|---|---|
| **Phase 01 = Space Analysis** · **Phase 02 = Functional Planning** | ✅ |
| **Phase 01 لا تبدأ Phase 02** | ✅ |
| **Analysis ≠ Proposal ≠ Approved Decision** | ✅ |
| **`[U]` ≠ `NOT_PRESENT` ≠ `VALUE`** | ✅ |
| **F Reference ≠ Fact** | ✅ |
| **Phase 01 لا يعتمد شيئًا** · **E يملك الاعتماد** | ✅ |
| **C3 يملك التوليد** · **D يملك fidelity** | ✅ |
| **B يملك Engineering Validation** · **A/B يملكان Data Integrity** | ✅ |
| **لا silent promotion · لا invention** | ✅ |

---

## 6. التحقق الوثائقي (A-05)

**لم يُكتب كود ولم يُشغَّل تنفيذ.** فحص اتساق **بلا تعديل ملفات**:

| الفحص | النتيجة |
|---|---|
| بصمات Schema · Template · RULES · Intake | **ثابتة** |
| بصمات A–F والطبقة التأسيسية | **ثابتة** |
| ملفات تنفيذية جديدة | **صفر** |
| الانحدار | **1377/1377 · REGRESSIONS: NONE** |

---

## 7. GATE CARD — R02 Delta

| البند | الحالة |
|---|---|
| **A-01** العقد الثلاثي `B Finding → Evidence → Classification` | ✅ **PASS** |
| **A-01** لا إعادة تفسير `severity` · لا تحويل تلقائي | ✅ **PASS** (CB-1/CB-2) |
| **A-01** التصنيف معلن باسم Phase 01 ولا يغيّر حكم B | ✅ **PASS** (CB-4) |
| **A-01** `UNRESOLVED / NOT_CLASSIFIED` بلا تخمين | ✅ **PASS** (CB-5) |
| **A-01** الفصل الثلاثي محفوظ | ✅ **PASS** (CB-6) |
| **A-02** Phase 01 ليس مصدرًا بديلًا للهندسة | ✅ **PASS** (GA-1…GA-8) |
| **A-02** المسار `Master → C3 → Output` محمي | ✅ **PASS** |
| **A-02** صياغة المسؤولية الثلاثية | ✅ **PASS** |
| **A-03** القرارات السبعة **OPEN** | ✅ **PASS** |
| **A-03** لا GAP/DEC جديد ولا مُغلق | ✅ **PASS** |
| **A-04** ما هو صحيح في R01 محفوظ | ✅ **PASS** |
| **A-05** لا كود · لا تنفيذ · الانحدار ثابت | ✅ **PASS** |
| تعارض جديد مع §5 أو A–F | ✅ **لا شيء** |

### الحالة

# **PHASE 01 — SPACE ANALYSIS — ARCHITECTURE R02 = READY FOR SUPERVISOR REVIEW**

# **IMPLEMENTATION = NOT AUTHORIZED**

**لم أكتب كودًا، ولم أعدّل Schema أو Master أو RULES أو Intake أو A–F أو الطبقة التأسيسية، ولم أغيّر نطاق Phase 01، ولم أحسم أي قرار مفتوح، ولم أغلق أي ثغرة.**
