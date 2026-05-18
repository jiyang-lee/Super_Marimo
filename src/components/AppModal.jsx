export function AppModal({ modalType, onClose, guideItems, sensorRows }) {
  const isSensorModal = modalType === "sensor";
  const modalTitle = isSensorModal ? "센서 안내" : "마리모 가이드";

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label={modalTitle}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <h3>{modalTitle}</h3>
          <button className="modal-close" type="button" onClick={onClose}>
            닫기
          </button>
        </div>

        {isSensorModal ? (
          <div className="modal-body">
            <p className="modal-description">
              이미지가 준비되면 이 공간에 실제 센서 설명과 시각 자료를 붙일 수
              있도록 구조만 먼저 잡아둔 상태입니다.
            </p>
            <ul className="modal-list">
              {sensorRows.map((row) => (
                <li key={row.title}>
                  <strong>{row.title}</strong>
                  <span>{row.note}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="modal-body">
            <ul className="guide-list">
              {guideItems.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong>
                  <span>{item.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
