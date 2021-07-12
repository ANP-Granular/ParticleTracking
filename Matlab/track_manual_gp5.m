%% track manual links
close all; clc; clear all;
image_folder =['/Volumes/Macintosh_HD/Germany/OVGU_MSE/HiWi/Granular/2021_02_Fallturm/GP12/1/'];
data_folder =['/Volumes/Macintosh_HD/Germany/OVGU_MSE/HiWi/Granular/2021_02_Fallturm/GP12/1/data_purple/'];
%mkdir(data_folder);
image_body =['GP12_'];
list = [0106, 0145, 0153, 0154, 0190, 0198, 0209, 0223, 0247, 0250, 0272, 0279, 0305, 0307, 0309, 0328, 0331, 0343, 0344, 0381, 0382, 0406, 0413, 0414, 0425, 0431, 0458, 0461, 0492, 0497, 0531, 0535, 0557, 0567, 0580, 0583, 0594, 0621, 0628, 0639, 0648, 0668, 0669, 0676, 0677, 0681, 0685, 0699, 0704, 0715, 0737, 0753, 0759, 0762, 0787];
num = length(list);
first_image = list(1,1); % first evaluable image % 0106
last_image = list(1,length(list)); % last evaluable image
color = 'data_purple';

%% track data
actual_rod_num =1; %actual rod to track
intervall = 1;
richtung = 1;  %1 wenn vorw�rts, -1 wenn r�ckw�rts
%%
tic
for item = 1:num
item % loop starts from first image value, increaments by 1 till it reaches last image
    current = list(item);
    image=imread([image_folder image_body num2str(current,'%05d') '.jpg']);
    %image=imread([image_folder num2str(i,'%05d') '.jpg']);
    imshow(image);hold on;
    try
    load([data_folder num2str(current,'%05d') '.mat']);  
       for n=1:1:(actual_rod_num-1)
         plot([rod_data_links(n).Point1(1),rod_data_links(n).Point2(1)],[rod_data_links(n).Point1(2),rod_data_links(n).Point2(2)],'-m','linewidth',2);   
       end;    
    end; 
     
    if current~=first_image   % check if both are not equal
    previous = list(item-1);
%     fprintf('yes i~=first_image: %d %d\n', current, first_image);
%     fprintf('Previous: %d\n', (previous));
    load([data_folder num2str(previous,'%05d') '.mat']);  
    plot([rod_data_links(actual_rod_num).Point1(1),rod_data_links(actual_rod_num).Point2(1)],[rod_data_links(actual_rod_num).Point1(2),rod_data_links(actual_rod_num).Point2(2)],'-c','linewidth',1); 
    mean_y=(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2;
    
% % Comment the following 'If' condition if we dont want to zoom-in on clicked area 
% %     if isnan(rod_data_links(actual_rod_num).Point1(1))==0
% %     xlim([(rod_data_links(actual_rod_num).Point1(1)+rod_data_links(actual_rod_num).Point2(1))/2-120,(rod_data_links(actual_rod_num).Point1(1)+rod_data_links(actual_rod_num).Point2(1))/2+120]);
% %     ylim([(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2-120,(rod_data_links(actual_rod_num).Point1(2)+rod_data_links(actual_rod_num).Point2(2))/2+120]);
% %     end;

    else
    mean_y=960;
%     fprintf('No,mean_y %d\n', mean_y);
    
    end; 
    try
    load([data_folder num2str(current,'%05d') '.mat']);  
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
   imwrite(WB_image,[data_folder image_body num2str(current,'%05d') '.jpg'],'Quality',90);
   %imwrite(WB_image,[data_folder num2str(i,'%05d') '.jpg'],'Quality',90);
   %saveas(1,[data_folder image_body num2str(i,'%04d') '.jpg']);
   save([data_folder num2str(current,'%05d') '.mat'], 'rod_data_links')

end;    
toc

