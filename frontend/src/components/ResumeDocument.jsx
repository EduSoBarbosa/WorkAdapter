import { useState } from 'react'
import { request, userPath, fetchPdf } from '../services/api'
import { ErrorBox, Form } from './UI'

export function TextList({ items=[] }) {
  return items.length ? <ul className="result-list">{items.map((item,i)=><li key={i}>{typeof item==='string'?item:item.texto||JSON.stringify(item)}</li>)}</ul> : null
}
export default function ResumeDocument({ value }) {
  if (!value) return <p>Currículo sem conteúdo.</p>
  if (typeof value.texto==='string') return <article className="resume-paper preserve">{value.texto}</article>
  if (!value.pessoa) return <article className="resume-paper"><p>Este currículo usa um formato antigo.</p><pre className="preserve">{JSON.stringify(value,null,2)}</pre></article>
  const p=value.pessoa
  return <article className="resume-paper"><h2>{p.nome_completo}</h2><p>{value.titulo}</p><p className="resume-contact">{[p.email,p.telefone,p.cidade,p.estado,p.pais].filter(Boolean).join(' · ')}</p>{[p.linkedin_url,p.github_url,p.portfolio_url].filter(Boolean).map(url=><p className="resume-contact" key={url}>{/^https?:\/\//i.test(url)?<a href={url} target="_blank" rel="noreferrer">{url}</a>:url}</p>)}
    {value.resumo&&<section className="resume-section"><h3>Resumo profissional</h3><p className="preserve">{value.resumo}</p></section>}
    {!!value.habilidades?.length&&<section className="resume-section"><h3>Habilidades</h3><p>{value.habilidades.join(' · ')}</p></section>}
    {[['experiencias','Experiências'],['projetos','Projetos'],['formacoes','Formação acadêmica'],['cursos','Cursos']].map(([key,label])=>value[key]?.length>0&&<section className="resume-section" key={key}><h3>{label}</h3>{value[key].map((item,i)=><div className="resume-entry" key={i}><h4>{item.cargo||item.nome||item.curso}</h4><p>{[item.empresa||item.instituicao,item.nivel,item.status].filter(Boolean).join(' · ')}</p><p className="resume-contact">{[item.data_inicio,item.atual?'Atual':item.data_fim||item.data_conclusao].filter(Boolean).join(' — ')}</p><TextList items={item.destaques}/>{!!item.stack?.length&&<p>Tecnologias: {item.stack.join(', ')}</p>}</div>)}</section>)}
    {!!value.idiomas?.length&&<section className="resume-section"><h3>Idiomas</h3>{value.idiomas.map((x,i)=><p key={i}>{[x.idioma,x.nivel,x.certificacao,x.pontuacao_certificacao].filter(v=>v!==null&&v!==undefined&&v!=='').join(' · ')}</p>)}</section>}
  </article>
}
export function PdfActions({ uid, cv }) {
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  async function getPdf(preview) {
    // Open in the click event to avoid popup blockers after the asynchronous fetch.
    const tab=preview?window.open('about:blank','_blank'):null
    if(preview&&!tab){setError('Permita abrir uma nova aba ou use Baixar PDF.');return}
    if(tab)tab.opener=null
    setBusy(true);setError('')
    try {
      const blob=await fetchPdf(uid,cv.id), url=URL.createObjectURL(blob)
      if(tab)tab.location.href=url
      else {const a=document.createElement('a');a.href=url;a.download=`${(cv.nome||'curriculo').replace(/[\\/:*?"<>|]/g,'-')}.pdf`;document.body.appendChild(a);a.click();a.remove()}
      setTimeout(()=>URL.revokeObjectURL(url),120000)
    } catch(e){tab?.close();setError(e.message)} finally{setBusy(false)}
  }
  return <div><div className="pdf-actions"><button className="button secondary" disabled={busy} onClick={()=>getPdf(true)}>Visualizar PDF</button><button className="button primary" disabled={busy} onClick={()=>getPdf(false)}>{busy?'Preparando PDF…':'Baixar PDF'}</button></div><ErrorBox>{error}</ErrorBox></div>
}
export function StructuredEditor({ cv, uid, onSaved, onCancel }) {
  const fields=[{key:'nome',label:'Nome desta versão',type:'text',required:true},{key:'resumo',label:'Resumo profissional',type:'textarea',required:true}]
  const initial={nome:cv.copy?`${cv.nome} (nova versão)`:cv.nome,resumo:cv.conteudo.resumo}
  for(const section of ['experiencias','projetos','formacoes','cursos']) (cv.conteudo[section]||[]).forEach((item,i)=>{const key=`${section}_${i}`;fields.push({key,label:`Destaques: ${item.cargo||item.nome||item.curso} (um por linha)`,type:'textarea'});initial[key]=(item.destaques||[]).join('\n')})
  return <><p className="muted">Revise o resumo e os destaques. Para corrigir instituições, datas ou contatos, atualize seu perfil e gere outro currículo.</p><Form fields={fields} initial={initial} onCancel={onCancel} onSubmit={async values=>{
    const conteudo=structuredClone(cv.conteudo);conteudo.resumo=values.resumo
    for(const section of ['experiencias','projetos','formacoes','cursos']) (conteudo[section]||[]).forEach((item,i)=>{item.destaques=(values[`${section}_${i}`]||'').split('\n').map(s=>s.trim()).filter(Boolean)})
    await request(`${userPath(uid)}/curriculos/${cv.id}${cv.copy?'/versoes':''}`,{method:cv.copy?'POST':'PATCH',body:{nome:values.nome,conteudo}});await onSaved()
  }}/></>
}
