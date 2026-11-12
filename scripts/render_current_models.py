from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'backend'))
from app.db import models
from app.db.base import Base
D=R/'docs/diagrams'
# Current relational exports are derived from ORM metadata, including every column.
out=D/'exports/sprint-09';out.mkdir(parents=True,exist_ok=True)
groups=[('01-cadastros',['users','projects','endpoints','test_scenarios']),('02-execucao-ia',['test_executions','metric_windows','model_versions','risk_predictions','control_decisions']),('03-relatorios-auditoria',['execution_reports','comparison_reports','comparison_report_executions','operation_logs'])]
regular=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',29)
for name,tables in groups:
    im=Image.new('RGB',(2200,1940),'white');dr=ImageDraw.Draw(im)
    dr.text((65,35),'LoadForge | Modelo relacional atual - Sprint 09',font=bold,fill='#193957')
    dr.text((65,82),'Cada painel lista colunas reais; FK identifica o destino sem linhas cruzadas.',font=regular,fill='#43566a')
    positions=[(65,150),(1150,150),(65,710),(1150,710),(65,1270)]
    for t,(x,y) in zip(tables,positions):
        table=Base.metadata.tables[t]
        dr.rounded_rectangle((x,y,x+980,y+515),radius=12,fill='#f4f7fa',outline='#bcccdc',width=2)
        dr.text((x+18,y+12),t,font=bold,fill='#193957')
        for i,c in enumerate(table.columns):
            flags=(' PK' if c.primary_key else '')+(' NULL' if c.nullable else '')
            fk='; FK '+','.join(f.target_fullname for f in c.foreign_keys) if c.foreign_keys else ''
            text=f'{c.name}: {c.type}{flags}{fk}'
            # Two lines only when a long composite description needs it.
            dr.text((x+18,y+60+i*23),text,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18),fill='#202b36')
    dr.text((65,1880),'Fonte: SQLAlchemy + schema.sql + migrations. Cabeça validada: 20261020_0007.',font=regular,fill='#43566a')
    im.save(out/(name+'.png'))
