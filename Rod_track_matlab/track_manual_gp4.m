%% track manual links
close all; clc; clear all;
image_folder =['/Volumes/Macintosh_HD/Germany/OVGU_MSE/HiWi/Granular/2020_12_Fallturm/shot9/GP3/'];
data_folder =['/Volumes/Macintosh_HD/Germany/OVGU_MSE/HiWi/Granular/2020_12_Fallturm/shot9/GP3/data_yellow/'];
%mkdir(data_folder);
image_body =['GP3_'];
%image_body=[''];
first_image = 0550; % first evaluable image
last_image = 0599; % last evaluable image
color = 'data_yellow';

%% track data
actual_rod_num =1; %actual rod to track
start_image = 0550; %image you want to start this session
end_image = 0599; %image you want to end this session
intervall = 1;
richtung = 1;  %1 wenn vorw�rts, -1 wenn r�ckw�rts
%%
tic
for i=start_image:richtung*intervall:end_image
i
    image=imread([image_folder image_body num2str(i,'%05d') '.jpg']);
    %image=imread([image_folder num2str(i,'%05d') '.jpg']);
    imshow(image);hold on;
    try
    load([data_folder num2str(i,'%05d') '.mat']);  
       for n=1:1:(actual_rod_num-1)
         plot([rod_data_links(n).Point1(1),rod_data_links(n).Point2(1)],[rod_data_links(n).Point1(2),rod_data_links(n).Point2(2)],'-m','linewidth',2);   
       end;    
    end; 
     
    if i~=first_image
    fprintf('yes i~=first_image %d %d\n', i, first_image)
    fprintf('Count %d\n', (i-richtung*intervall))
    load([data_folder num2str(i-richtung*intervall,'%05d') '.mat']);  
    plot([rod_data_links(actual_rod_num).Point1(1),rod_data_links(actual_rod_num).Point2(1)],[rod_data_links(actual_rod_num).Point1(2),rod_data_links(actual_rod_num).Point2(2)],'-c','linewidth',1); 
    mean_y=(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2;
    if isnan(rod_data_links(actual_rod_num).Point1(1))==0
    xlim([(rod_data_links(actual_rod_num).Point1(1)+rod_data_links(actual_rod_num).Point2(1))/2-120,(rod_data_links(actual_rod_num).Point1(1)+rod_data_links(actual_rod_num).Point2(1))/2+120]);
    ylim([(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2-120,(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2+120]);
    end;
    
    else
    mean_y=960;
    fprintf('mean_y=960\n', 960)
    end; 
    
    try
    load([data_folder num2str(i,'%05d') '.mat']);  
    end;
    
    %if length(rod_data_links)>=actual_rod_num && i==first_image
    %    text(0,200,'St�bchen ist schon angeklickt!!!','FontSize',28)
    %end;
   
    % x=[0 0]';
    % y=[0 0]';
    [x,y]=ginput(2);% Ausklammern, wenn Postion aus erstem Bild eingetragen werden soll
    if ((y(1)>=mean_y+120)|(y(1)>=960));
    x(:)=NaN;    
    y(:)=NaN; 
    end;    
    rod_data_links(actual_rod_num).Point1(1)=x(1);
    rod_data_links(actual_rod_num).Point1(2)=y(1);
    rod_data_links(actual_rod_num).Point2(1)=x(2);
    rod_data_links(actual_rod_num).Point2(2)=y(2);
hold off;
    
    imshow(image);hold on;
    WB_image=image;
    for n=1:1:size(rod_data_links,2)
     try   
     plot([rod_data_links(n).Point1(1),rod_data_links(n).Point2(1)],[rod_data_links(n).Point1(2),rod_data_links(n).Point2(2)],'-m','linewidth',2);
     % Computer vision function
     shapeInserter=vision.ShapeInserter('Shape','lines','LineWidth',1,'BorderColor','Custom','CustomBorderColor',[0 255 255]);
     WB_image = step(shapeInserter, WB_image, uint32([rod_data_links(n).Point1(1),rod_data_links(n).Point1(2),rod_data_links(n).Point2(1),rod_data_links(n).Point2(2)])); 
     end;
    end;   
    for n=1:1:size(rod_data_links,2)
        try
          text((rod_data_links(n).Point1(1)+rod_data_links(n).Point2(1))/2,(rod_data_links(n).Point1(2)+rod_data_links(n).Point2(2))/2,num2str(n),'BackgroundColor',[1 1 1],'HorizontalAlignment','center');
          WB_image = insertText(WB_image,[(rod_data_links(n).Point1(1)+rod_data_links(n).Point2(1))/2-10,(rod_data_links(n).Point1(2)+rod_data_links(n).Point2(2))/2-15],num2str(n),'FontSize',18,'BoxColor','white','BoxOpacity',0.5,'TextColor','black');
        end;
     end;  
   %print('-f1','-djpeg','-r200',[data_folder image_body num2str(i,'%04d') '.jpg']);
   imwrite(WB_image,[data_folder image_body num2str(i,'%05d') '.jpg'],'Quality',90);
   %imwrite(WB_image,[data_folder num2str(i,'%05d') '.jpg'],'Quality',90);
   %saveas(1,[data_folder image_body num2str(i,'%04d') '.jpg']);
   save([data_folder num2str(i,'%05d') '.mat'], 'rod_data_links')

end;    
toc

