/* =
   script.js
   이 파일에서 하는 일은 크게 5가지입니다.
   1) 스크롤해서 화면에 보이는 요소들을 서서히 나타나게 하기
   2) 캐릭터 아이콘(memoji)에 마우스를 올리면 소개 문구 보여주기
   3) 오른쪽 아래 "맨 위로" 버튼 눌렀을 때 스크롤 맨 위로 이동시키기
   4) Projects 기술스택 필터 버튼 처리
   5) Projects 카드 "더보기" 토글 처리
   */


/* 
   1) 스크롤하면 서서히 나타나는 애니메이션
   IntersectionObserver는 "이 요소가 화면 안에 들어왔는지"를 감시해주는
   브라우저 기능입니다. 화면에 들어오면 is-visible 클래스를 붙여서
   style.css에 정의해둔 트랜지션이 실행되게 합니다.

   요소가 화면 밖으로 나가면 is-visible 클래스를 다시 지워서, 스크롤을
   위/아래로 왔다갔다 할 때마다 매번 다시 나타나도록 했습니다. (한 번
   보여준 뒤 계속 그대로 두면 스크롤을 되돌렸을 때 반응이 없어서 뭔가
   빠진 것처럼 느껴졌습니다.)
*/
const aosTargets = document.querySelectorAll("[data-aos]");

const aosObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      } else {
        entry.target.classList.remove("is-visible");
      }
    });
  },
  {
    threshold: 0.15, // 요소가 15% 정도 보이면 나타난 것으로 판단
  }
);

aosTargets.forEach((target) => aosObserver.observe(target));

/* 
   2) 캐릭터 아이콘(memoji) 호버 효과
   마우스를 올리면(is-hover 클래스 추가) 이름/생일/학교 정보가 나타나고,
   마우스를 떼면 다시 사라집니다. 실제 나타나고 사라지는 움직임은
   style.css의 transition으로 처리하고, 여기서는 클래스만 붙였다 뗐다 합니다.
 */
const memoji = document.getElementById("memoji");
if (memoji) {
  memoji.addEventListener("mouseenter", () => {
    memoji.classList.add("is-hover");
  });
  memoji.addEventListener("mouseleave", () => {
    memoji.classList.remove("is-hover");
  });
}

/* 
   3) 맨 위로 이동 버튼
 */
const scrollTopBtn = document.getElementById("scrollTopBtn");
if (scrollTopBtn) {
  scrollTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

/* 
   4) Projects 기술스택 필터
   필터 버튼(전체/React/Vue/React Native)을 누르면, 각 프로젝트 카드에
   미리 붙여둔 data-stack 값과 클릭한 버튼의 data-filter 값을 비교해서,
   맞지 않는 카드에는 is-filtered-out 클래스를 붙여 숨깁니다.
 */
const filterButtons = document.querySelectorAll(".project-filter__btn");
const projectBoxes = document.querySelectorAll(".project-box");

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    // 버튼들의 강조(is-active) 표시를 클릭한 버튼 하나로만 옮겨줍니다.
    filterButtons.forEach((b) => b.classList.remove("is-active"));
    btn.classList.add("is-active");

    const selected = btn.dataset.filter; // "all" | "react" | "vue" | "react-native"

    projectBoxes.forEach((box) => {
      const matches = selected === "all" || box.dataset.stack === selected;
      box.classList.toggle("is-filtered-out", !matches);
    });
  });
});

/* 
   5) Projects 카드 "더보기" 토글
   기본적으로 접혀 있는 상세 설명 목록을 버튼을 누를 때마다 펼치고
   접습니다. 버튼 글자도 "더보기"/"접기"로 함께 바뀝니다.
 */
document.querySelectorAll(".project-box__toggle").forEach((toggleBtn) => {
  toggleBtn.addEventListener("click", () => {
    const card = toggleBtn.closest(".project-box");
    const isExpanded = card.classList.toggle("is-expanded");

    // 화살표 회전은 CSS에서 처리하고, 여기서는 버튼 앞쪽 글자만 바꿔줍니다.
    const arrow = toggleBtn.querySelector(".project-box__toggle-arrow");
    toggleBtn.firstChild.textContent = isExpanded ? "접기 " : "더보기 ";
    arrow.textContent = "⌄";
  });
});

/* 
   6) GITHUB / BLOG / RESUME 버튼
   버튼마다 data-link 속성(github/blog/resume)이 붙어있는데, 그걸 보고
   아래 linkUrls 객체에서 실제 주소를 찾아서 엽니다. 주소를 아직 안 정한
   버튼(빈 문자열 "")은 window.open 대신 안내 문구만 뜨도록 했습니다.
 */
const linkUrls = {
  github: "https://github.com/axie190",
  blog: "",   // 블로그 주소가 정해지면 여기에 주소를 입력 합니다.
  resume: "", // 이력서 주소가 정해지면 여기에 주소를 입력 합니다.
};

document.querySelectorAll(".info__button").forEach((btn) => {
  btn.addEventListener("click", () => {
    const label = btn.dataset.link || btn.title || "링크";
    const url = linkUrls[label];

    if (url) {
      window.open(url, "_blank");
    } else {
      alert(`[${label}] 이동할 실제 주소를 아직 연결하지 않았습니다.`);
    }
  });
});

/* 
   7) 프로젝트 카드의 GitHub / 사이트 링크 아이콘
   프로젝트마다 실제 저장소/사이트 주소가 다른데 아직 정해두지 않아서,
   지금은 눌러도 안내 문구만 뜨도록 해뒀습니다. 나중에 프로젝트별 주소가
   생기면, index.html의 각 icon-btn에 예를 들어 data-url="실제주소" 를
   추가하고 여기서 btn.dataset.url을 열도록 바꾸면 됩니다.
 */
document.querySelectorAll(".icon-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const label = btn.dataset.icon || btn.title || "링크";
    alert(`[${label}] 이동할 실제 주소를 아직 연결하지 않았습니다.`);
  });
});
