import { useEffect, useId, useRef, useState } from 'react'

const paths = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  user: 'M20 21v-2a7 7 0 0 0-14 0v2 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  file: 'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  briefcase: 'M3 7h18v14H3z M8 7V3h8v4 M3 12l9 4 9-4 M12 12v5',
  plus: 'M12 5v14 M5 12h14', arrow: 'M5 12h14 M14 7l5 5-5 5',
  close: 'M6 6l12 12 M18 6 6 18', check: 'm5 12 4 4 10-10',
  spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
  layers: 'm12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',
  book: 'M12 5C8 2 4 3 2 4v16c3-2 7-2 10 0 3-2 7-2 10 0V4c-3-1-7-2-10 1z M12 5v15',
  graduation: 'm2 8 10-5 10 5-10 5z M6 10v7c4 3 8 3 12 0v-7 M22 8v9',
  globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c5 5 5 13 0 18-5-5-5-13 0-18',
  search: 'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0 M15 15l6 6',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 6v6l4 2',
  edit: 'm15 4 5 5 M3 21l2-7L16 3l5 5L10 19z',
  trash: 'M3 6h18 M9 6V3h6v3 M6 6l1 15h10l1-15 M10 10v7 M14 10v7',
}
export function Icon({ name='spark', size=20 }) { return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.spark}/></svg> }
export function Empty({ title, children, action, icon='layers' }) { return <div className="empty"><span className="empty-icon"><Icon name={icon} size={28}/></span><h3>{title}</h3><p>{children}</p>{action}</div> }
export function PageHeading({ eyebrow, title, children, action }) { return <header className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{children}</p></div>{action}</header> }
export function ErrorBox({ children }) { return children ? <div className="error-box" role="alert">{children}</div> : null }
export function Modal({ title, children, onClose }) {
  const ref = useRef(null); const titleId=useId()
  useEffect(() => { const dialog=ref.current; dialog.showModal(); return () => dialog.close() }, [])
  return <dialog ref={ref} aria-labelledby={titleId} onCancel={e => {e.preventDefault();onClose()}}><div className="modal-head"><h2 id={titleId}>{title}</h2><button className="icon-button" aria-label="Fechar janela" onClick={onClose}><Icon name="close"/></button></div>{children}</dialog>
}
export function Form({ fields, initial={}, onSubmit, onCancel, submitLabel='Salvar', children }) {
  const [values,setValues]=useState(() => Object.fromEntries(fields.map(f => [f.key, f.type==='checkbox' ? Boolean(initial[f.key]) : String(initial[f.key] ?? (f.required && f.options ? Object.keys(f.options)[0] : ''))])))
  const [busy,setBusy]=useState(false); const [error,setError]=useState('')
  const id=useId()
  async function submit(e) {
    e.preventDefault();setError('');setBusy(true)
    try {
      const body=Object.fromEntries(fields.map(f => [f.key, f.type==='checkbox' ? Boolean(values[f.key]) : values[f.key]==='' ? null : f.type==='number' ? Number(values[f.key]) : values[f.key].trim()]))
      if (body.data_inicio && (body.data_fim || body.data_conclusao) && (body.data_fim || body.data_conclusao)<body.data_inicio) throw new Error('A data final precisa ser igual ou posterior à data de início.')
      if(body.atual && body.data_fim) throw new Error('Para um trabalho atual, deixe a data de término vazia.')
      await onSubmit(body)
    } catch(err) {setError(err.message)} finally {setBusy(false)}
  }
  return <form onSubmit={submit}><p className="form-note">Campos com * são obrigatórios.</p><fieldset disabled={busy}><div className="form-grid">{fields.map(f => <div className={`field ${f.type==='textarea' ? 'wide' : ''} ${f.type==='checkbox'?'check-field':''}`} key={f.key}><label htmlFor={`${id}-${f.key}`}>{f.label}{f.required && ' *'}</label>{f.type==='textarea' ? <textarea id={`${id}-${f.key}`} rows={4} value={values[f.key]} required={f.required} onChange={e=>setValues({...values,[f.key]:e.target.value})}/> : f.options ? <select id={`${id}-${f.key}`} required={f.required} value={values[f.key]} onChange={e=>setValues({...values,[f.key]:e.target.value})}>{!f.required && <option value="">Não informado</option>}{values[f.key] && !(values[f.key] in f.options) && <option value={values[f.key]}>{values[f.key]}</option>}{Object.entries(f.options).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select> : <input id={`${id}-${f.key}`} type={f.type} required={f.required} min={f.type==='number'?0:undefined} step={f.type==='number'?'any':undefined} maxLength={['text','email','tel'].includes(f.type)?200:undefined} checked={f.type==='checkbox'?values[f.key]:undefined} value={f.type==='checkbox'?undefined:values[f.key]} onChange={e=>setValues({...values,[f.key]:f.type==='checkbox'?e.target.checked:e.target.value})}/>}</div>)}</div>{children}</fieldset><ErrorBox>{error}</ErrorBox><div className="form-actions"><button type="button" className="button ghost" disabled={busy} onClick={onCancel}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Salvando…':submitLabel}<Icon name="check" size={16}/></button></div></form>
}
export function Confirm({ title, description, onConfirm, onClose }) {
  const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  return <Modal title={title} onClose={()=>!busy&&onClose()}><p className="confirm-text">{description}</p><ErrorBox>{error}</ErrorBox><div className="form-actions"><button className="button ghost" disabled={busy} onClick={onClose}>Cancelar</button><button className="button danger" disabled={busy} onClick={async()=>{setBusy(true);try{await onConfirm()}catch(e){setError(e.message)}finally{setBusy(false)}}}>{busy?'Excluindo…':'Excluir'}</button></div></Modal>
}
