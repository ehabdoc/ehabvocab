// قائمة الكلمات يتم تمريرها من Flask عبر المتغير العام vocabularyWords

let currentWordIndex = 0; // مؤشر لتتبع الكلمة الحالية
let reviewedWordsCount = 0;
let knownWordsCount = 0;
let needsReviewWordsCount = 0;

// الحصول على عناصر عرض الكلمة والترجمة
const currentWordDisplay = document.getElementById('currentWord');
const translationDisplay = document.getElementById('currentTranslation');
const feedbackMessage = document.getElementById('feedbackMessage'); // العنصر الذي يعرض رسائل التغذية الراجعة

// الحصول على الأزرار
const showTranslationBtn = document.getElementById('showTranslationBtn');
const speakBtn = document.getElementById('speakBtn');
const knowButton = document.querySelector('.btn-know');
const needReviewButton = document.querySelector('.btn-need-review');
const endSessionBtn = document.getElementById('endSessionBtn'); // زر إنهاء الجلسة

// دالة لإرسال تقدم المستخدم إلى الخادم
async function recordProgress(wordId, status) {
    try {
        const response = await fetch('/record_progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ word_id: wordId, status: status }),
        });
        const data = await response.json();
        console.log('Progress record response:', data);
    } catch (error) {
        console.error('Error recording progress:', error);
    }
}

// دالة لعرض الكلمة الحالية
function displayCurrentWord() {
    console.log("displayCurrentWord called.");
    console.log("vocabularyWords:", vocabularyWords);

    if (vocabularyWords && vocabularyWords.length > 0 && currentWordIndex < vocabularyWords.length) {
        const wordData = vocabularyWords[currentWordIndex];
        currentWordDisplay.textContent = wordData.word;
        translationDisplay.textContent = wordData.translation;
        translationDisplay.style.display = 'none'; // إخفاء الترجمة في البداية
        feedbackMessage.textContent = ''; // مسح رسالة التغذية الراجعة
        
        // إظهار الأزرار
        showTranslationBtn.style.display = 'inline-block';
        speakBtn.style.display = 'inline-block';
        knowButton.style.display = 'inline-block';
        needReviewButton.style.display = 'inline-block';

    } else {
        // عندما لا توجد المزيد من الكلمات أو لا توجد كلمات في قاعدة البيانات
        currentWordDisplay.textContent = "لقد أكملت جميع الكلمات في هذه الجلسة!";
        translationDisplay.textContent = "انقر على 'إنهاء الجلسة' لمراجعة ملخص أدائك.";
        translationDisplay.style.display = 'block';
        
        // إخفاء الأزرار المتعلقة بالكلمة الحالية
        showTranslationBtn.style.display = 'none';
        speakBtn.style.display = 'none';
        knowButton.style.display = 'none';
        needReviewButton.style.display = 'none';
        // إظهار زر إنهاء الجلسة إذا كان مخفياً
        endSessionBtn.style.display = 'inline-block'; 
    }
}

// إضافة مستمعي الأحداث للأزرار

// زر إظهار الترجمة
showTranslationBtn.addEventListener('click', function() {
    translationDisplay.style.display = 'block';
});

// زر تشغيل النطق
speakBtn.addEventListener('click', function() {
    const wordToSpeak = currentWordDisplay.textContent;
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(wordToSpeak);
        utterance.lang = 'en-US';
        speechSynthesis.speak(utterance);
    } else {
        alert('متصفحك لا يدعم النطق الصوتي.');
    }
});

// زر "أعرفها جيداً"
knowButton.addEventListener('click', function() {
    reviewedWordsCount++;
    knownWordsCount++;
    if (vocabularyWords[currentWordIndex]) {
        recordProgress(vocabularyWords[currentWordIndex].id, 'known');
    }
    feedbackMessage.textContent = 'أحسنت! استمر هكذا.';
    feedbackMessage.style.color = '#28a745'; // لون أخضر
    setTimeout(() => {
        currentWordIndex++;
        displayCurrentWord();
    }, 1000); // الانتقال بعد ثانية واحدة
});

// زر "أحتاج لمراجعة"
needReviewButton.addEventListener('click', function() {
    reviewedWordsCount++;
    needsReviewWordsCount++;
    if (vocabularyWords[currentWordIndex]) {
        recordProgress(vocabularyWords[currentWordIndex].id, 'needs_review');
    }
    feedbackMessage.textContent = 'لا تقلق، المراجعة هي مفتاح الإتقان! ستتقنها قريباً.';
    feedbackMessage.style.color = '#dc3545'; // لون أحمر
    setTimeout(() => {
        currentWordIndex++;
        displayCurrentWord();
    }, 1000); // الانتقال بعد ثانية واحدة
});

// زر إنهاء الجلسة (ينتقل إلى صفحة الملخص)
endSessionBtn.addEventListener('click', function() {
    // حفظ إحصائيات الجلسة في sessionStorage قبل الانتقال
    sessionStorage.setItem('reviewed_count', reviewedWordsCount);
    sessionStorage.setItem('known_count', knownWordsCount);
    sessionStorage.setItem('needs_review_count', needsReviewWordsCount);
    window.location.href = 'summary.html';
});

// استدعاء الدالة لأول مرة عند تحميل الصفحة لعرض الكلمة الأولى
document.addEventListener('DOMContentLoaded', displayCurrentWord);