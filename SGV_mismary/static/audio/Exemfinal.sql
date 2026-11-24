create database Ecoruta;

use Ecoruta;

create table conductores (
	id_conductores int primary key auto_increment,
    nombreconductor varchar(50),
    sede varchar(50)
);

insert into conductores (nombreconductor,sede)
values
	("Sebastián Rojas","ibague"),
    ("Valentina Méndez","bogota"),
    ("Felipe Vargas","neiva"),
    ("Daniela Castillo","cali"),
    ("Mauricio Herrera","pereira");

select * from conductores;

create table transporte(
	id_servicio int primary key,
    conductor_id int,
    tiposervicio varchar(50),
    viaje int,
    tarifaviaje int,
    
    foreign key (conductor_id) references conductores(id_conductores)
);
insert into  transporte(id_servicio,conductor_id,tiposervicio,viaje,tarifaviaje)
values
	(201,1,"Intermunicipal",18,920000),
    (202,1,"Empresarial",12,650000),
    (203,2,"Intermunicipal",25,920000),
    (204,2,"Especial",15,780000),
    (205,3,"Empresarial",20,650000),
    (206,3,"Urbano",35,180000),
    (207,4,"Especial",22,780000),
    (208,4,"Intermunicipal",14,920000),
    (209,5,"Urbano",30,180000),
    (210,5,"Empresarial",10,650000);
    
select * from transporte;

-- PROBLEMA 1 BBUAJAJJAAJ
SELECT c.nombreconductor,SUM(t.viaje * t.tarifaviaje) AS IngresoTotal,SUM(t.viaje) AS TotalViajes
FROM conductores c
INNER JOIN transporte t
ON c.id_conductores = t.conductor_id
GROUP BY c.id_conductores, c.nombreconductor
HAVING SUM(t.viaje * t.tarifaviaje) > 18000000
ORDER BY IngresoTotal DESC;

-- Pregunta 2
create table TipoRespuesto(
	tipoID int primary key auto_increment,
    NombreTipo varchar(100)
);
insert into TipoRespuesto(NombreTipo)
values
	("Motor y transmisión"),
    ("Sistema eléctrico"),
    ("Frenos y suspensión"),
    ("Lubricantes y filtros");
    

CREATE TABLE Repuesto (
    repuestoID INT PRIMARY KEY AUTO_INCREMENT,
    NombreRepuesto VARCHAR(100),
    tipoID INT,
    CostoUnitario INT,
    Existencias INT,

    FOREIGN KEY (tipoID) REFERENCES TipoRespuesto(tipoID)
);

INSERT INTO Repuesto (NombreRepuesto, tipoID, CostoUnitario, Existencias)
VALUES
    ("Kit de embrague", 1, 1800000, 12),
    ("Caja de cambios", 1, 5200000, 6),
    ("Correa distribución", 1, 850000, 18),
    ("Alternador", 2, 1250000, 10),
    ("Batería", 2, 950000, 22),
    ("Sensor electrónico", 2, 480000, 30),
    ("Discos de freno", 3, 620000, 25),
    ("Amortiguador", 3, 780000, 18),
    ("Pastillas de freno", 3, 240000, 35),
    ("Aceite sintético", 4, 280000, 45),
    ("Filtro de aire", 4, 95000, 60),
    ("Filtro de aceite", 4, 75000, 80);

SELECT * FROM Repuesto;
-- PROBLEMA 2 ESTA DIFICIL
SELECT t.NombreTipo,COUNT(r.repuestoID) AS TotalRepuestos,AVG(r.CostoUnitario) AS CostoPromedio,SUM(r.CostoUnitario * r.Existencias) AS ValorInventario
FROM TipoRespuesto t
INNER JOIN Repuesto r
ON t.tipoID = r.tipoID
GROUP BY t.tipoID, t.NombreTipo
HAVING SUM(r.CostoUnitario * r.Existencias) > 25000000
ORDER BY ValorInventario DESC;

-- PREGUNTA 3 :(

CREATE TABLE EmpresasContratantes (
    ContratanteID INT PRIMARY KEY AUTO_INCREMENT,
    RazonSocial VARCHAR(100),
    Ciudad VARCHAR(50)
);

INSERT INTO EmpresasContratantes (RazonSocial, Ciudad)
VALUES
    ("Transportes del Centro", "Ibagué"),
    ("Logística Integral SAS", "Bogotá"),
    ("Carga Express", "Medellín"),
    ("Movilidad Andina", "Ibagué"),
    ("Distribuciones del Norte", "Bogotá"),
    ("Servicios Ruta Sur", "Neiva"),
    ("Transportes del Centro", "Ibagué");

CREATE TABLE AliadosTransporte (
    AliadoID INT PRIMARY KEY AUTO_INCREMENT,
    RazonSocial VARCHAR(100),
    Ciudad VARCHAR(50)
);

INSERT INTO AliadosTransporte (RazonSocial, Ciudad)
VALUES
    ("Operadora Nacional", "Bogotá"),
    ("Transportes del Centro", "Ibagué"),
    ("Soluciones de Carga", "Medellín"),
    ("Movilidad del Pacífico", "Cali"),
    ("Operadora Nacional", "Bogotá"),
    ("Red de Transporte", "Neiva"),
    ("Logística Integral SAS", "Bogotá");

SELECT * FROM EmpresasContratantes;

SELECT * FROM AliadosTransporte;

-- PROBLEMA 3 :(
SELECT Ciudad,TipoRelacion,COUNT(*) AS TotalRegistros
FROM (SELECT Ciudad,'Contratante' AS TipoRelacion
    FROM EmpresasContratantes
    UNION ALL
    SELECT Ciudad,'Aliado' AS TipoRelacion
    FROM AliadosTransporte
) AS Relaciones
GROUP BY Ciudad, TipoRelacion
ORDER BY TotalRegistros DESC, Ciudad ASC;
-- PREGUNTA 4 espero alcanzar

create table Conductores2(
	conductorId int primary key auto_increment,
    NombreConductor_2 varchar(100),
    licencia varchar(50)
);

INSERT INTO Conductores2 (NombreConductor_2, licencia)
VALUES
    ('Julián Ramírez', 'C2'),
    ('Andrea López', 'C3'),
    ('Ricardo Torres', 'C2'),
    ('Natalia Castro', 'C3');

create table Vehiculos(
	vehiculosID varchar(50) primary key,
    Placa varchar(20),
    CapacidadToneladas int
);

insert into Vehiculos(vehiculosID,Placa,CapacidadToneladas)
values
	(101,"TOL123",4),
    (102,"BOG456",8),
    (103,"HUI789",5),
    (104,"CAL321",12);

select * from Vehiculos;

create table Asignaciones(
	asignacionID int primary key,
    conductorID int,
    FechaAsignacion date,

	foreign key (conductorID) references Conductores2(conductorId)
);

insert into Asignaciones(asignacionID,conductorID,FechaAsignacion)
values
	(601,1,2026-11-02),
    (602,2,2026-11-04),
    (603,3,	2026-11-06),
    (604,1,2026-11-08);

-- NO SUPE CON INSERTAR DATOS DE TIPO FECHA :(
    
create table Asignaciones2(
	asignacionID int primary key,
    conductorID int,
    FechaAsignacion varchar(100),

	foreign key (conductorID) references Conductores2(conductorId)
);
insert into Asignaciones2(asignacionID,conductorID,FechaAsignacion)
values
	(601,1,"2026-11-02"),
    (602,2,"2026-11-04"),
    (603,3,	"2026-11-06"),
    (604,1,"2026-11-08");
    
select * from  Asignaciones2;

create table DetalleAsignacion(
	detalleID int primary key auto_increment,
    asignacionID int,
    VehiculoId int,
    Kilometros int,
    
    foreign key (asignacionID) references Asignaciones2(asignacionID),
    foreign key(
);



