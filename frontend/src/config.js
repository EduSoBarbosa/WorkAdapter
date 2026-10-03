export const statuses = {
  salva: 'Salva', enviada: 'Candidatura enviada', em_andamento: 'Em andamento',
  oferta_recebida: 'Oferta recebida', aprovada: 'Aprovada', reprovada: 'Reprovada',
  desistencia: 'Desistência', vaga_encerrada: 'Vaga encerrada',
}
const f = (key, label, type = 'text', required = false, options) => ({ key, label, type, required, options })
const dates = [f('data_inicio', 'Data de início', 'date'), f('data_fim', 'Data de término / previsão', 'date')]
const study = f('status', 'Situação', 'select', true, { cursando: 'Cursando', concluido: 'Concluído', interrompido: 'Interrompido' })
export const personalFields = [
  f('nome_completo', 'Nome completo', 'text', true), f('vaga_alvo_atual', 'Vaga alvo atual'),
  f('email', 'E-mail', 'email'), f('telefone', 'Telefone', 'tel'), f('cidade', 'Cidade'),
  f('estado', 'Estado'), f('pais', 'País'), f('linkedin_url', 'LinkedIn', 'url'),
  f('github_url', 'GitHub', 'url'), f('portfolio_url', 'Portfólio', 'url'),
  f('resumo_profissional', 'Resumo profissional', 'textarea'),
]
export const sections = {
  experiencias: { label: 'Experiências', singular: 'experiência', icon: 'briefcase', fields: [f('cargo', 'Cargo', 'text', true), f('empresa', 'Empresa', 'text', true), f('tipo_vinculo', 'Tipo de vínculo'), f('localidade', 'Localidade'), ...dates, f('atual', 'Trabalho aqui atualmente', 'checkbox'), f('descricao', 'Atividades realizadas', 'textarea'), f('resultados', 'Resultados e contribuições', 'textarea')] },
  formacoes: { label: 'Formação', singular: 'formação', icon: 'graduation', fields: [f('instituicao', 'Instituição', 'text', true), f('curso', 'Curso', 'text', true), f('nivel', 'Nível / titulação'), study, ...dates, f('descricao', 'Descrição', 'textarea')] },
  cursos: { label: 'Cursos', singular: 'curso', icon: 'book', fields: [f('nome', 'Nome do curso', 'text', true), f('instituicao', 'Instituição'), f('carga_horaria', 'Carga horária (horas)', 'number'), study, f('data_inicio', 'Data de início', 'date'), f('data_conclusao', 'Data de conclusão', 'date'), f('certificado_url', 'Link do certificado', 'url'), f('descricao', 'O que você aprendeu', 'textarea')] },
  projetos: { label: 'Projetos', singular: 'projeto', icon: 'layers', fields: [f('nome', 'Nome do projeto', 'text', true), f('papel_desempenhado', 'Seu papel'), ...dates, f('repositorio_url', 'Repositório', 'url'), f('demonstracao_url', 'Demonstração', 'url'), f('descricao', 'Descrição do projeto', 'textarea'), f('resultados', 'Resultados e contribuições', 'textarea')] },
  idiomas: { label: 'Idiomas', singular: 'idioma', icon: 'globe', fields: [f('idioma', 'Idioma', 'text', true), f('nivel', 'Nível', 'select', false, { 'Básico': 'Básico', 'Intermediário': 'Intermediário', 'Avançado': 'Avançado', 'Fluente': 'Fluente', 'Nativo': 'Nativo', A1:'A1', A2:'A2', B1:'B1', B2:'B2', C1:'C1', C2:'C2' }), f('certificacao', 'Certificação'), f('pontuacao_certificacao', 'Pontuação')] },
}
export const applicationFields = [
  f('titulo_vaga', 'Título da vaga', 'text', true), f('empresa', 'Empresa', 'text', true),
  f('nome', 'Apelido da candidatura'), f('plataforma', 'Plataforma'),
  f('tipo_contrato', 'Tipo de contrato'), f('modalidade', 'Modalidade', 'select', false, { remoto: 'Remoto', hibrido: 'Híbrido', presencial: 'Presencial' }),
  f('localidade', 'Localidade'), f('data_candidatura', 'Data da candidatura', 'date'),
  f('url_vaga', 'Link da vaga', 'url'), f('descricao', 'Descrição da vaga', 'textarea'),
  f('observacoes', 'Suas anotações', 'textarea'),
]
export function dateLabel(value) {
  if (!value) return 'Não informada'
  const [y,m,d] = value.slice(0,10).split('-')
  return `${d}/${m}/${y}`
}
export function timeLabel(value) {
  if (!value) return 'Sem movimentação'
  return new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}
