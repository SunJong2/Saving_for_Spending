// 모아사 서비스워커
// 전략: network-first (온라인이면 항상 최신, 오프라인이면 캐시된 정적 파일로 폴백)
// - 개발 중 "왜 수정이 반영 안 되지" 문제를 피하려고 캐시 우선이 아니라 네트워크 우선
// - API 응답(/goals, /savings 등 동적·인증 데이터)은 절대 캐시하지 않음

const CACHE = "moasa-v1";   // 정적 파일 캐시 무효화하려면 버전 숫자만 올리면 됨

// 설치: 곧바로 활성화 대기 없이 넘어감
self.addEventListener("install", (e) => {
    self.skipWaiting();
});

// 활성화: 옛 버전 캐시 청소 + 즉시 제어권 확보
self.addEventListener("activate", (e) => {
    e.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
            ))
            .then(() => self.clients.claim())
    );
});

// 요청 가로채기
self.addEventListener("fetch", (e) => {
    const req = e.request;

    // 쓰기 요청(POST/PATCH/DELETE)은 건드리지 않음 → 그대로 네트워크로
    if (req.method !== "GET") return;

    const url = new URL(req.url);

    // 외부 도메인 요청은 패스
    if (url.origin !== location.origin) return;

    // 정적 앱 셸(/static/ 아래)만 캐싱 대상. API 경로는 손대지 않음
    if (!url.pathname.startsWith("/static/")) return;

    e.respondWith(
        fetch(req)
            .then((res) => {
                // 최신 응답을 캐시에 복사해둠 (다음 오프라인 대비)
                const copy = res.clone();
                caches.open(CACHE).then((c) => c.put(req, copy));
                return res;
            })
            .catch(() => caches.match(req))   // 네트워크 실패(오프라인) → 캐시로 폴백
    );
});
